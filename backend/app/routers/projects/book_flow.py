"""Explicit approval gates and sequential page generation for the Studio."""

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_adult_user
from app.models import Job, JobStatus, JobType, User
from app.printkit.service import invalidate_print
from app.schemas import JobAcceptedOut, ProjectOut
from app.services import book_profile, jobs, purchase_flow

from .common import accept_job, get_owned_project

router = APIRouter()


def _project(db, user, project_id):
    project = get_owned_project(db, user, project_id)
    if not book_profile.enabled(project):
        raise HTTPException(409, "Projeto anterior ao novo fluxo do Studio")
    if db.scalar(
        select(Job.id).where(
            Job.project_id == project.id,
            Job.status.in_([JobStatus.PENDING.value, JobStatus.RUNNING.value]),
        )
    ):
        raise HTTPException(409, "Aguarde a geracao atual terminar")
    return project


@router.post("/{project_id}/story/approve", response_model=ProjectOut)
def approve_story(
    project_id: uuid.UUID,
    user: User = Depends(require_adult_user),
    db: Session = Depends(get_db),
):
    project = _project(db, user, project_id)
    book_profile.require_real_preview(project)
    book_profile.require_stage(project, "story_ready", "story_approved")
    book_profile.update(project, stage="story_approved")
    db.commit()
    return project


class PageIn(BaseModel):
    page: int | None = Field(default=None, ge=1, le=16)
    adjustment: str | None = Field(default=None, max_length=500)


@router.post("/{project_id}/pages/next", response_model=JobAcceptedOut, status_code=202)
def next_page(
    project_id: uuid.UUID,
    body: PageIn | None = None,
    user: User = Depends(require_adult_user),
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    # An uncertain HTTP response can be retried without duplicating image charges.
    project = get_owned_project(db, user, project_id)
    if idempotency_key:
        existing = db.scalar(
            select(Job).where(Job.project_id == project.id, Job.idempotency_key == idempotency_key)
        )
        if existing:
            return accept_job(existing)
    project = _project(db, user, project_id)
    purchase_flow.require_paid(db, project)
    if project.book_approved_at:
        raise HTTPException(409, "O livro ja foi aprovado para impressao")
    purchase_flow.update(project, full_book_ready_at=None)
    book_profile.require_stage(project, "avatar_approved", "page_ready", "book_ready")
    current = project.book_profile.get("current_page", 0)
    number = body.page if body and body.page else current + 1
    if number > min(current + 1, 16):
        raise HTTPException(409, "Gere as paginas em ordem, uma por vez")
    project.book_approved_at = None
    invalidate_print(db, project)
    return accept_job(
        jobs.enqueue_job(
            db,
            user=user,
            project=project,
            job_type=JobType.EBOOK,
            idempotency_key=idempotency_key,
            payload={
                "master_page": True,
                "page": number,
                "adjustment": body.adjustment if body else None,
            },
        )
    )


@router.get("/{project_id}/preview/package")
def preview_package(
    project_id: uuid.UUID, user: User = Depends(require_adult_user), db: Session = Depends(get_db)
):
    import hashlib
    import io
    import tempfile
    import zipfile

    from fastapi.responses import StreamingResponse
    from PIL import Image
    from starlette.background import BackgroundTask

    from app import storage
    from app.models import Asset
    from app.services import editorial_profile
    from app.services.privacy import require_photo_authorization

    project = get_owned_project(db, user, project_id)
    require_photo_authorization(db, project.id)
    if not (project.purchase_flow or {}).get("preview_ready_at"):
        raise HTTPException(409, "Aguarde a prévia atual terminar")
    assets = db.scalars(select(Asset).where(Asset.project_id == project.id)).all()
    output = tempfile.TemporaryFile()
    digests = set()
    try:
        # PNGs are already compressed; keep the archive on disk, not in API RAM.
        with zipfile.ZipFile(output, "w", zipfile.ZIP_STORED) as archive:
            for lang in [project.language or "pt-BR"]:
                for role in editorial_profile.ROLES:
                    matches = [
                        a
                        for a in assets
                        if (a.meta or {}).get("workflow") == 1
                        and a.meta.get("language") == lang
                        and a.meta.get("role") == role
                        and (
                            a.meta.get("validation", {}).get("status") == "valid"
                            or (
                                a.meta.get("validation", {}).get("status") == "awaiting_user_review"
                                and a.meta.get("validation", {}).get("reviewer") == "user"
                                and a.meta.get("validation", {}).get("method")
                                == "technical_integrity_only"
                            )
                        )
                        and (
                            not project.book_profile.get("editorial")
                            or a.meta.get("editorial") == project.book_profile["editorial"]
                        )
                    ]
                    if len(matches) != 1:
                        raise HTTPException(
                            409, "Aguarde três imagens validadas antes de baixar o pacote"
                        )
                    asset = matches[0]
                    if asset.meta.get("texts") != project.book_profile["locales"][lang]:
                        raise HTTPException(409, "Atualize as imagens para os textos atuais")
                    data = storage.get_bytes(asset.storage_key)
                    if role == "03_LEITURA":
                        covers = [
                            a
                            for a in assets
                            if (a.meta or {}).get("language") == lang
                            and a.meta.get("role") == "01_CAPA"
                            and a.meta.get("workflow") == 1
                        ]
                        if (
                            len(covers) != 1
                            or asset.meta.get("cover_sha256")
                            != hashlib.sha256(storage.get_bytes(covers[0].storage_key)).hexdigest()
                        ):
                            raise HTTPException(409, "Atualize a leitura para a capa atual")
                    with Image.open(io.BytesIO(data)) as image:
                        if image.format != "PNG":
                            raise HTTPException(409, "Arquivo de prévia inválido")
                        image.verify()
                    digest = hashlib.sha256(data).hexdigest()
                    if digest in digests:
                        raise HTTPException(409, "O pacote contém imagens duplicadas")
                    digests.add(digest)
                    title = project.book_profile["locales"][lang]["title"]
                    archive.writestr(book_profile.filename(lang, role, title), data)
    except BaseException:
        output.close()
        raise
    output.seek(0)

    def chunks():
        try:
            while chunk := output.read(64 * 1024):
                yield chunk
        finally:
            output.close()

    return StreamingResponse(
        chunks(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="Storyrus-previa.zip"'},
        background=BackgroundTask(output.close),
    )
