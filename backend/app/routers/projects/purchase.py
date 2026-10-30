"""The customer's path from preview to quotation and final approval."""

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_adult_user
from app.models import JobType, User
from app.printkit.service import get_print_order, invalidate_print, open_print_order
from app.schemas import JobAcceptedOut, PrintOrderOut, ProjectOut
from app.services import jobs, purchase_flow
from app.services.preview_chain import PREVIEW_FLAG

from .common import accept_job, get_owned_project

router = APIRouter()


class PreviewChangesIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    theme_description: str = Field(min_length=1, max_length=500)
    story_text: str = Field(default="", max_length=50000)
    photo_notes: str = Field(default="", max_length=500)


class PreviewTitleIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class TitleSuggestionsIn(BaseModel):
    guidance: str = Field(default="", max_length=500)


class TitleSuggestionsOut(BaseModel):
    titles: list[str]


@router.post("/{project_id}/preview/title-suggestions", response_model=TitleSuggestionsOut)
async def suggest_titles(
    project_id: uuid.UUID,
    body: TitleSuggestionsIn,
    user: User = Depends(require_adult_user),
    db: Session = Depends(get_db),
):
    from app.ai_clients import get_text_provider
    from app.ai_clients.base import ProviderError
    from app.rate_limit import allow
    from app.services.privacy import require_photo_authorization

    project = get_owned_project(db, user, project_id)
    editable_title(db, project)
    require_photo_authorization(db, project.id)
    if not allow(f"title-suggestions:{user.id}", 5, 3600):
        raise HTTPException(429, "Limite de sugestões atingido. Tente novamente mais tarde.")
    profile = project.book_profile or {}
    language = project.language or "pt-BR"
    story = (profile.get("stories") or {}).get(language) or project.story_text or ""
    context = {
        "title": profile.get("title", ""),
        "theme": profile.get("theme_description") or project.theme,
        "protagonist": project.child_name,
        "age": project.child_age,
        "language": language,
        "story": story[:12000],
    }
    try:
        titles = await get_text_provider().suggest_titles(context=context, guidance=body.guidance.strip())
    except ProviderError as exc:
        raise HTTPException(502, "Não foi possível gerar os títulos com IA. Tente novamente.") from exc
    return TitleSuggestionsOut(titles=titles)


def editable(db, project):
    order = get_print_order(db, project.id)
    if order and order.payment_status in {"paid", "pending"}:
        raise HTTPException(
            409, "O pedido já está em pagamento ou produção. Entre em contato para ajustes."
        )
    if purchase_flow.active_job(db, project):
        raise HTTPException(409, "Aguarde a geração terminar antes de continuar.")


def editable_title(db, project):
    """A pending checkout locks prices and delivery, but may still refine its title."""
    from app.services import book_profile

    order = get_print_order(db, project.id)
    if order and order.payment_status == "paid":
        raise HTTPException(409, "O livro já está em produção. Solicite ajustes na revisão final.")
    if purchase_flow.active_job(db, project):
        raise HTTPException(409, "Aguarde a geração terminar antes de continuar.")
    book_profile.require_stage(
        project, "preview_ready", "story_ready", "story_approved", "preview_approved"
    )
    if (project.book_profile or {}).get("current_page", 0) or project.book_approved_at:
        raise HTTPException(409, "Solicite ajustes na revisão final do livro.")


class SpecificationIn(BaseModel):
    book_size: str = Field(pattern="^(M|P)$")
    cover_type: str = Field(pattern="^(soft|hard)$")


@router.put("/{project_id}/print-order/specification", response_model=PrintOrderOut)
def save_specification(
    project_id: uuid.UUID,
    body: SpecificationIn,
    user: User = Depends(require_adult_user),
    db: Session = Depends(get_db),
):
    from app.config import settings
    from app.printkit.service import _clear_freight

    from .print import to_print_out

    project = get_owned_project(db, user, project_id)
    editable(db, project)
    order = get_print_order(db, project.id)
    if not order or not (project.purchase_flow or {}).get("preview_approved_at"):
        raise HTTPException(409, "Aprove a prévia antes de configurar o pedido.")
    if body.book_size == "P" and body.cover_type == "hard" and not settings.print_allow_p_hardcover:
        raise HTTPException(409, "O formato 15 × 15 cm em capa dura ainda não está disponível.")
    project.book_size, project.cover_type = body.book_size, body.cover_type
    order.book_size, order.cover_type = body.book_size, body.cover_type
    _clear_freight(order)
    purchase_flow.update(project, quoted_at=None)
    db.commit()
    return to_print_out(order)


@router.put("/{project_id}/preview/title", response_model=JobAcceptedOut, status_code=202)
def save_title(
    project_id: uuid.UUID,
    body: PreviewTitleIn,
    user: User = Depends(require_adult_user),
    db: Session = Depends(get_db),
):
    """Atualiza o título e refaz só a capa, sem apagar a história nem voltar a etapa."""
    project = get_owned_project(db, user, project_id)
    editable_title(db, project)
    from app.services import book_profile

    book_profile.apply_title(project, body.title)
    return accept_job(
        jobs.enqueue_job(
            db,
            user=user,
            project=project,
            job_type=JobType.EBOOK,
            payload={"master_preview": True, "title_refresh": True, "image": "01_CAPA"},
            idempotency_key=f"preview-title-{project.id}-{uuid.uuid4()}",
        )
    )


@router.put("/{project_id}/preview/changes", response_model=JobAcceptedOut, status_code=202)
def save_changes(
    project_id: uuid.UUID,
    body: PreviewChangesIn,
    user: User = Depends(require_adult_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user, project_id)
    editable(db, project)
    from app.services import book_profile

    if book_profile.enabled(project):
        book_profile.require_stage(project, "preview_ready")
        if not body.title.strip() or not body.theme_description.strip():
            raise HTTPException(422, "Preencha título e tema.")
        from sqlalchemy import select

        from app.models import Asset

        for asset in db.scalars(select(Asset).where(Asset.project_id == project.id)).all():
            if (asset.meta or {}).get("workflow") == 1:
                db.delete(asset)
        book_profile.update(
            project,
            title=body.title.strip(),
            theme_description=body.theme_description.strip(),
            locales=None,
            stories=None,
            stage="ficha",
            current_page=0,
        )
        purchase_flow.update(
            project,
            title=body.title.strip(),
            theme_description=body.theme_description.strip(),
            photo_notes=body.photo_notes.strip(),
            preview_ready_at=None,
            preview_approved_at=None,
            quoted_at=None,
            stage="preview_generating",
        )
        project.book_approved_at = None
        project.ebook_url = None
        invalidate_print(db, project)
        return accept_job(
            jobs.enqueue_job(
                db,
                user=user,
                project=project,
                job_type=JobType.EBOOK,
                payload={
                    PREVIEW_FLAG: True,
                    "master_preview": True,
                    "adjustment": body.photo_notes.strip(),
                },
                idempotency_key=f"preview-changes-{project.id}-{uuid.uuid4()}",
            )
        )
    if not project.character_ref:
        raise HTTPException(409, "Gere a prévia antes de enviar alterações.")
    if not all([body.title.strip(), body.theme_description.strip(), body.story_text.strip()]):
        raise HTTPException(422, "Preencha título, tema e história.")
    text = body.story_text.strip()
    title_line = f"Título: {body.title.strip()}"
    if re.match(r"^(?:T[íi]tulo|Title)\s*:", text, re.I):
        text = re.sub(
            r"^(?:T[íi]tulo|Title)\s*:[^\n]*", lambda _: title_line, text, count=1, flags=re.I
        )
    else:
        text = title_line + "\n\n" + text
    project.story_text = text
    project.book_approved_at = None
    project.preview_notified_at = None
    invalidate_print(db, project)
    purchase_flow.update(
        project,
        title=body.title.strip(),
        theme_description=body.theme_description.strip(),
        photo_notes=body.photo_notes.strip(),
        preview_approved_at=None,
        quoted_at=None,
        preview_ready_at=None,
        stage="preview_generating",
        full_book_ready_at=None,
    )
    # Saving all fields and scheduling the updated artwork are one transaction.
    return accept_job(
        jobs.enqueue_job(
            db,
            user=user,
            project=project,
            job_type=JobType.EBOOK,
            idempotency_key=f"preview-changes-{project.id}-{uuid.uuid4()}",
            payload={PREVIEW_FLAG: True},
        )
    )


@router.post("/{project_id}/preview/approve", response_model=ProjectOut)
def approve_preview(
    project_id: uuid.UUID,
    user: User = Depends(require_adult_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user, project_id)
    editable(db, project)
    from app.services import book_profile

    master = book_profile.enabled(project)
    if master:
        book_profile.require_stage(project, "story_approved", "preview_approved")
    if not master and (not project.story_text or not project.ebook_url):
        raise HTTPException(409, "Aguarde a prévia ficar pronta antes de aprovar.")
    if not master and not (project.purchase_flow or {}).get("preview_ready_at"):
        # Older previews also need a successfully completed preview job.
        from sqlalchemy import select

        from app.models import Job, JobStatus

        last = db.scalar(
            select(Job)
            .where(Job.project_id == project.id, Job.type == "EBOOK")
            .order_by(Job.created_at.desc())
            .limit(1)
        )
        if (
            not last
            or last.status != JobStatus.DONE.value
            or (last.result or {}).get("preview_complete") is False
        ):
            raise HTTPException(
                409, "A prévia ainda está incompleta. Gere novamente antes de aprovar."
            )
    project.book_approved_at = None
    if master:
        book_profile.update(project, stage="preview_approved")
    purchase_flow.update(
        project,
        preview_ready_at=(project.purchase_flow or {}).get("preview_ready_at")
        or purchase_flow.timestamp(),
        preview_approved_at=purchase_flow.timestamp(),
        stage="awaiting_payment",
    )
    order = open_print_order(db, project, prepare=False)
    order.book_size, order.cover_type = project.book_size, project.cover_type
    order.status = "awaiting_payment"
    order.cover_key = order.interior_key = None
    order.block_reason = None
    project.print_status = order.status
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/quotation", response_model=ProjectOut)
def save_quotation(
    project_id: uuid.UUID,
    user: User = Depends(require_adult_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user, project_id)
    editable(db, project)
    if not (project.purchase_flow or {}).get("preview_approved_at"):
        raise HTTPException(409, "Aprove a prévia antes de salvar a cotação.")
    purchase_flow.update(project, quoted_at=purchase_flow.timestamp())
    db.commit()
    return project


@router.post("/{project_id}/book/generate", response_model=JobAcceptedOut, status_code=202)
def generate_book(
    project_id: uuid.UUID,
    user: User = Depends(require_adult_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user, project_id)
    order = get_print_order(db, project.id)
    if not order:
        raise HTTPException(409, "Aprove a prévia e confirme o pedido primeiro.")
    try:
        job = purchase_flow.enqueue_paid_book(db, order, retry=True)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return accept_job(job)


class BookChangesIn(BaseModel):
    notes: str = Field(min_length=3, max_length=500)


@router.post("/{project_id}/book/changes", response_model=JobAcceptedOut, status_code=202)
def revise_book(
    project_id: uuid.UUID,
    body: BookChangesIn,
    user: User = Depends(require_adult_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, user, project_id)
    if (project.book_profile or {}).get("version") == 1:
        raise HTTPException(
            409, "Solicite o ajuste na página correspondente antes de aprovar o livro."
        )
    order = get_print_order(db, project.id)
    flow = project.purchase_flow or {}
    if not body.notes.strip() or not flow.get("full_book_ready_at") or project.book_approved_at:
        raise HTTPException(409, "Solicite ajustes antes de aprovar o livro para impressão.")
    if not order or order.payment_status != "paid" or purchase_flow.active_job(db, project):
        raise HTTPException(409, "Aguarde a confirmação do pedido e o fim da geração.")
    purchase_flow.update(
        project,
        final_notes=body.notes.strip(),
        book_revision=int(flow.get("book_revision", 0)) + 1,
        full_book_ready_at=None,
    )
    return accept_job(purchase_flow.enqueue_paid_book(db, order))
