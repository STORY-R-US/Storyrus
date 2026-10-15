"""Disparo de etapas do pipeline (202 Accepted) e inputs de história."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import story_import, story_templates
from app.config import settings
from app.database import get_db
from app.deps import require_registered_user
from app.models import (
    Asset,
    AssetKind,
    Job,
    JobStatus,
    JobType,
    Project,
    ProjectStatus,
    User,
    UserVoice,
)
from app.observability.context import get_request_id
from app.printkit.service import invalidate_print
from app.schemas import (
    JobAcceptedOut,
    NarratedVideoRequestIn,
    PreviewRequestIn,
    ProjectOut,
    StoryExtractOut,
    StoryRequestIn,
    StoryTemplateApplyIn,
    StoryTextIn,
    VideoRequestIn,
)
from app.services import book_profile, preview_chain
from app.services import jobs as jobs_svc

from .common import accept_job, get_owned_project

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{project_id}/avatar", response_model=JobAcceptedOut, status_code=202)
def start_avatar(
    project_id: uuid.UUID,
    user: User = Depends(require_registered_user),
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> JobAcceptedOut:
    project = get_owned_project(db, user, project_id)
    book_profile.require_stage(project, "story_approved", "avatar_ready")
    has_photo = db.scalar(
        select(Asset).where(Asset.project_id == project.id, Asset.kind == AssetKind.PHOTO.value)
    )
    if not has_photo:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Envie ao menos uma foto antes")
    project.character_approved_at = None
    project.book_approved_at = None
    # Pedido impresso antigo não pode impedir o avatar (mesma proteção da prévia).
    try:
        invalidate_print(db, project)
    except Exception:  # noqa: BLE001 - avatar segue mesmo se o impresso antigo falhar
        logger.exception("invalidate_print falhou project=%s", project.id)
        db.rollback()
        project = get_owned_project(db, user, project_id)
        project.character_approved_at = None
        project.book_approved_at = None
    job = jobs_svc.enqueue_job(
        db, user=user, project=project, job_type=JobType.AVATAR, idempotency_key=idempotency_key
    )
    return accept_job(job)


@router.post("/{project_id}/realistic", response_model=JobAcceptedOut, status_code=202)
def start_realistic(
    project_id: uuid.UUID,
    user: User = Depends(require_registered_user),
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> JobAcceptedOut:
    """Legado: gera imagem extra a partir da foto. O vídeo usa o avatar 3D (character_ref)."""
    project = get_owned_project(db, user, project_id)
    has_photo = db.scalar(
        select(Asset).where(Asset.project_id == project.id, Asset.kind == AssetKind.PHOTO.value)
    )
    if not has_photo:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Envie ao menos uma foto antes")
    job = jobs_svc.enqueue_job(
        db, user=user, project=project, job_type=JobType.REALISTIC, idempotency_key=idempotency_key
    )
    return accept_job(job)


@router.post("/{project_id}/story", response_model=JobAcceptedOut, status_code=202)
def start_story(
    project_id: uuid.UUID,
    body: StoryRequestIn | None = None,
    user: User = Depends(require_registered_user),
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> JobAcceptedOut:
    """Inventar uma história com IA (Claude)."""
    project = get_owned_project(db, user, project_id)
    book_profile.require_stage(project, "preview_approved", "story_ready")
    payload: dict | None = None
    brief = (body.brief if body else None) or None
    if brief and brief.strip():
        payload = {"brief": brief.strip()[:2000]}
    job = jobs_svc.enqueue_job(
        db,
        user=user,
        project=project,
        job_type=JobType.STORY,
        idempotency_key=idempotency_key,
        payload=payload,
    )
    return accept_job(job)


@router.post("/{project_id}/preview", response_model=JobAcceptedOut, status_code=202)
def start_preview(
    project_id: uuid.UUID,
    body: PreviewRequestIn | None = None,
    user: User = Depends(require_registered_user),
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> JobAcceptedOut:
    """Gera a prévia no Studio: avatar → história → ebook (3 págs) → vídeo.

    Auto-aprova personagem e livro ao longo da cadeia. Requer foto. Bloqueia se
    já houver uma prévia PENDING/RUNNING no projeto.
    """
    project = get_owned_project(db, user, project_id)
    has_photo = db.scalar(
        select(Asset).where(Asset.project_id == project.id, Asset.kind == AssetKind.PHOTO.value)
    )
    if not has_photo:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Envie ao menos uma foto antes")

    # Idempotência antes do conflito: retry com a mesma chave devolve o job ativo.
    if idempotency_key:
        existing = db.scalar(select(Job).where(Job.idempotency_key == idempotency_key))
        if existing is not None:
            if existing.project_id != project.id:
                raise HTTPException(409, "Chave de geracao ja utilizada em outro projeto")
            return accept_job(existing)

    if preview_chain.has_active_preview(db, project.id):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Já existe uma prévia em andamento para este projeto",
        )

    if book_profile.enabled(project):
        book_profile.require_stage(project, "ficha", "preview_ready")
        photos = db.scalars(
            select(Asset).where(Asset.project_id == project.id, Asset.kind == AssetKind.PHOTO.value)
        ).all()
        book_profile.validate_ficha(project, photos)
        payload = {preview_chain.PREVIEW_FLAG: True, "master_preview": True}
        if body:
            payload.update(body.model_dump(exclude_none=True, exclude={"brief"}))
        if payload.get("language") and payload["language"] not in project.book_profile["languages"]:
            raise HTTPException(400, "Idioma nao pertence a ficha deste livro")
        project.book_approved_at = None
        return accept_job(
            jobs_svc.enqueue_job(
                db,
                user=user,
                project=project,
                job_type=JobType.EBOOK,
                idempotency_key=idempotency_key,
                payload=payload,
            )
        )

    payload: dict = {preview_chain.PREVIEW_FLAG: True}
    brief = (body.brief if body else None) or None
    if brief and brief.strip():
        payload["brief"] = brief.strip()[:2000]

    project.character_approved_at = None
    project.book_approved_at = None
    # Pedido impresso antigo não pode impedir a prévia. Falha aqui (tabela,
    # linha ruim) era 500 "Erro interno" depois de "Projeto criado".
    try:
        invalidate_print(db, project)
    except Exception:  # noqa: BLE001 - prévia segue mesmo se o impresso antigo falhar
        logger.exception("invalidate_print falhou project=%s", project.id)
        db.rollback()
        project = get_owned_project(db, user, project_id)
        project.character_approved_at = None
        project.book_approved_at = None

    ref = project.character_ref if isinstance(project.character_ref, dict) else {}
    demo_character = ref.get("provider") == "demo"
    if ref and not ref.get("provider"):
        last_avatar = db.scalar(
            select(Job)
            .where(
                Job.project_id == project.id,
                Job.type == JobType.AVATAR.value,
                Job.status == JobStatus.DONE.value,
            )
            .order_by(Job.created_at.desc())
            .limit(1)
        )
        demo_character = bool(last_avatar is not None and last_avatar.cost_usd == 0)
    if project.character_ref and not demo_character:
        job_type = JobType.STORY
        step = "story"
    else:
        job_type = JobType.AVATAR
        step = "avatar"

    # Sem Idempotency-Key do cliente: UUID novo para permitir re-gerar após DONE.
    key = idempotency_key or f"preview-{project.id}-{step}-{uuid.uuid4()}"
    job = jobs_svc.enqueue_job(
        db,
        user=user,
        project=project,
        job_type=job_type,
        idempotency_key=key,
        payload=payload,
    )
    return accept_job(job)


@router.post("/{project_id}/story/text", response_model=ProjectOut)
def set_story_text(
    project_id: uuid.UUID,
    body: StoryTextIn,
    user: User = Depends(require_registered_user),
    db: Session = Depends(get_db),
) -> Project:
    """Usar uma história fornecida pelo usuário (digitada ou colada). Sem IA, sem créditos."""
    project = get_owned_project(db, user, project_id)
    book_profile.require_stage(project, "story_ready")
    text = body.story_text.strip()
    if not text:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "História vazia")
    project.story_text = text
    if book_profile.enabled(project):
        from app.workers.handlers.common import _parse_pages, _parse_title

        if (
            len(_parse_pages(text)) != 16
            or _parse_title(text) != project.book_profile["locales"][project.language]["title"]
        ):
            raise HTTPException(400, "Preserve o titulo aprovado e as 16 paginas")
        book_profile.update(
            project, stories={**project.book_profile["stories"], project.language: text}
        )
    project.status = ProjectStatus.STORY_READY.value
    rid = get_request_id()
    # Registra um job concluído para a história aparecer no progresso, sem custo.
    db.add(
        Job(
            project_id=project.id,
            type=JobType.STORY.value,
            status=JobStatus.DONE.value,
            cost_credits=0,
            attempts=1,
            request_id=rid,
            result={"source": "user"},
        )
    )
    # Em background: gera o roteiro completo (storyboard) do vídeo, sem custo.
    db.add(
        Job(
            project_id=project.id,
            type=JobType.STORYBOARD.value,
            status=JobStatus.PENDING.value,
            cost_credits=0,
            request_id=rid,
            result={"payload": {"auto": True, "source": "user_story"}},
        )
    )
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/story/template", response_model=ProjectOut)
def apply_story_template(
    project_id: uuid.UUID,
    body: StoryTemplateApplyIn,
    user: User = Depends(require_registered_user),
    db: Session = Depends(get_db),
) -> Project:
    """Usar uma história pronta do catálogo, personalizada com o nome da criança.

    Sem IA, sem créditos: o texto do template vai direto para story_text no formato
    padrão ('Título:' + 'Página N:'), com {NOME} substituído pelo nome do projeto.
    """
    project = get_owned_project(db, user, project_id)
    if book_profile.enabled(project):
        raise HTTPException(409, "A historia deste livro e criada depois de aprovar a previa")
    name = (project.child_name or "").strip()
    if not name:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Defina o nome da criança no projeto antes de usar uma história pronta",
        )
    try:
        text = story_templates.render_template(body.template_id, name, gender=body.gender)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "História não encontrada no catálogo")
    project.story_text = text
    project.status = ProjectStatus.STORY_READY.value
    rid = get_request_id()
    # Registra um job concluído para a história aparecer no progresso, sem custo.
    db.add(
        Job(
            project_id=project.id,
            type=JobType.STORY.value,
            status=JobStatus.DONE.value,
            cost_credits=0,
            attempts=1,
            request_id=rid,
            result={"source": "template", "template_id": body.template_id},
        )
    )
    # Em background: gera o roteiro completo (storyboard) do vídeo, sem custo.
    db.add(
        Job(
            project_id=project.id,
            type=JobType.STORYBOARD.value,
            status=JobStatus.PENDING.value,
            cost_credits=0,
            request_id=rid,
            result={"payload": {"auto": True, "source": "template_story"}},
        )
    )
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/story/extract", response_model=StoryExtractOut)
async def extract_story(
    project_id: uuid.UUID,
    user: User = Depends(require_registered_user),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
) -> StoryExtractOut:
    """Extrai o texto de um arquivo (PDF/DOCX/DOC/TXT) para o usuário revisar e salvar."""
    get_owned_project(db, user, project_id)
    data = await file.read()
    if len(data) > 5_000_000:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Arquivo muito grande (máx. 5MB)"
        )
    try:
        text = story_import.extract_text(file.filename or "", data)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Não consegui ler o arquivo: {exc}"
        )
    if not text.strip():
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Não encontrei texto neste arquivo."
        )
    return StoryExtractOut(text=text)


@router.post("/{project_id}/ebook", response_model=JobAcceptedOut, status_code=202)
def start_ebook(
    project_id: uuid.UUID,
    user: User = Depends(require_registered_user),
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> JobAcceptedOut:
    project = get_owned_project(db, user, project_id)
    if book_profile.enabled(project):
        raise HTTPException(409, "Use a etapa de paginas: uma pagina por vez apos aprovar o rosto")
    project.book_approved_at = None
    # Pedido impresso antigo não pode impedir o ebook.
    try:
        invalidate_print(db, project)
    except Exception:  # noqa: BLE001 - ebook segue mesmo se o impresso antigo falhar
        logger.exception("invalidate_print falhou project=%s", project.id)
        db.rollback()
        project = get_owned_project(db, user, project_id)
        project.book_approved_at = None
    job = jobs_svc.enqueue_job(
        db, user=user, project=project, job_type=JobType.EBOOK, idempotency_key=idempotency_key
    )
    return accept_job(job)


@router.post("/{project_id}/extra-character", response_model=JobAcceptedOut, status_code=202)
def start_extra_character(
    project_id: uuid.UUID,
    user: User = Depends(require_registered_user),
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> JobAcceptedOut:
    """Gera os personagens ilustrados para todas as fotos de personagens extras enviadas."""
    project = get_owned_project(db, user, project_id)
    extras = project.extra_characters or []
    if not extras:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Envie ao menos uma foto de personagem extra"
        )
    job = jobs_svc.enqueue_job(
        db,
        user=user,
        project=project,
        job_type=JobType.EXTRA_CHARACTER,
        idempotency_key=idempotency_key,
    )
    return accept_job(job)


@router.post("/{project_id}/video", response_model=JobAcceptedOut, status_code=202)
def start_video(
    project_id: uuid.UUID,
    body: VideoRequestIn,
    user: User = Depends(require_registered_user),
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> JobAcceptedOut:
    project = get_owned_project(db, user, project_id)
    payload = {
        "duration_s": body.duration_s or settings.default_video_duration_s,
        "provider": body.provider or settings.video_provider,
    }
    job = jobs_svc.enqueue_job(
        db,
        user=user,
        project=project,
        job_type=JobType.VIDEO,
        idempotency_key=idempotency_key,
        payload=payload,
    )
    return accept_job(job)


@router.post("/{project_id}/narrated-video", response_model=JobAcceptedOut, status_code=202)
def start_narrated_video(
    project_id: uuid.UUID,
    body: NarratedVideoRequestIn | None = None,
    user: User = Depends(require_registered_user),
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> JobAcceptedOut:
    project = get_owned_project(db, user, project_id)
    if not (project.story_text or "").strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Historia ausente")
    payload: dict = {}
    voice_id = body.voice_id if body else None
    if voice_id is not None:
        voice = db.get(UserVoice, voice_id)
        if voice is None or voice.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Voz nao encontrada")
        payload["voice_id"] = str(voice.id)
    job = jobs_svc.enqueue_job(
        db,
        user=user,
        project=project,
        job_type=JobType.NARRATED_VIDEO,
        idempotency_key=idempotency_key,
        payload=payload,
    )
    return accept_job(job)
