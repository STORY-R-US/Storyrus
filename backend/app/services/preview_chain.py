"""Cadeia automática de prévia no Studio: avatar → história → ebook (trio OpenAI).

O job inicial (POST /preview) carrega `payload.preview_chain=true`. Ao concluir
cada etapa, o worker auto-aprova o necessário e enfileira a próxima — até o
EBOOK, que gera capa + 1 página + foto na mão via GPT Image. Sem VIDEO.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job, JobStatus, JobType, Project, User, _now
from app.services import jobs as jobs_svc

logger = logging.getLogger(__name__)

PREVIEW_FLAG = "preview_chain"
_CHAIN_TYPES = (
    JobType.AVATAR.value,
    JobType.STORY.value,
    JobType.EBOOK.value,
)


def job_payload(job: Job) -> dict:
    return (job.result or {}).get("payload", {}) if job.result else {}


def is_preview_chain(job: Job) -> bool:
    return bool(job_payload(job).get(PREVIEW_FLAG))


def has_active_preview(db: Session, project_id: uuid.UUID) -> bool:
    """True se já há etapa da cadeia de prévia PENDING/RUNNING neste projeto.

    Uma linha com JSON ilegível não pode derrubar POST /preview com 500.
    """
    try:
        jobs = db.scalars(
            select(Job).where(
                Job.project_id == project_id,
                Job.status.in_([JobStatus.PENDING.value, JobStatus.RUNNING.value]),
                Job.type.in_(_CHAIN_TYPES),
            )
        ).all()
        return any(is_preview_chain(j) for j in jobs)
    except Exception:  # noqa: BLE001 - leitura da fila não pode virar HTTP 500
        logger.exception("has_active_preview falhou project=%s", project_id)
        db.rollback()
        return False


def _next_payload(source_job: Job, next_type: JobType) -> dict:
    src = job_payload(source_job)
    out: dict = {PREVIEW_FLAG: True}
    brief = (src.get("brief") or "").strip()
    if brief and next_type == JobType.STORY:
        out["brief"] = brief[:2000]
    return out


def finalize_preview_ebook(db: Session, project: Project, source_job: Job) -> None:
    """Marca o livro aprovado ao fim da prévia (sem enfileirar vídeo)."""
    if not is_preview_chain(source_job):
        return
    project.book_approved_at = _now()
    # Só avisa o cliente uma vez: a marca é gravada antes do envio (at-most-once).
    notify_email = _preview_recipient(db, project) if project.preview_notified_at is None else None
    if project.preview_notified_at is None:
        project.preview_notified_at = _now()
    child_name = (project.child_name or "").strip()
    nested = db.begin_nested()
    try:
        from app.printkit.service import open_print_order

        open_print_order(db, project, requested=False)
        nested.commit()
    except Exception:
        nested.rollback()
        logger.exception("os da previa falhou project=%s", project.id)
    db.commit()
    logger.info("preview_chain finalized at EBOOK project=%s", project.id)
    if notify_email:
        _send_preview_ready_notice(notify_email, child_name)


def _preview_recipient(db: Session, project: Project) -> str | None:
    """E-mail do cliente para o aviso de prévia pronta (None se guest/sem e-mail)."""
    from app.security import is_guest_user

    try:
        user = db.get(User, project.user_id)
    except Exception:
        logger.exception("preview_ready: user lookup falhou project=%s", project.id)
        return None
    if user is None:
        return None
    email = (user.email or "").strip()
    if not email or is_guest_user(email=email, password_hash=user.password_hash or ""):
        logger.info("preview_ready_email_skipped project=%s reason=guest_or_no_email", project.id)
        return None
    return email


def _send_preview_ready_notice(to_email: str, child_name: str) -> None:
    """Envia o aviso de prévia pronta sem derrubar o job (best-effort)."""
    from app.services.transactional_email import send_preview_ready_email

    try:
        send_preview_ready_email(to_email=to_email, child_name=child_name)
    except Exception:
        logger.exception("preview_ready_email falhou to=%s", to_email)


def continue_preview_chain(
    db: Session,
    project: Project,
    source_job: Job,
    next_type: JobType,
) -> Job | None:
    """Se o job concluído é de prévia, auto-aprova e enfileira a próxima etapa.

    Em backpressure / teto de gasto (e em falta de créditos, se o sistema
    estiver ligado): cria um job FAILED (sem débito) para a UI mostrar o erro
    — não falha o job já concluído.
    """
    if not is_preview_chain(source_job):
        return None

    if next_type == JobType.STORY:
        project.character_approved_at = _now()
    elif next_type == JobType.EBOOK:
        pass
    else:
        return None

    db.flush()

    user = db.get(User, project.user_id)
    if user is None:
        logger.error("preview_chain: user ausente project=%s", project.id)
        return None

    payload = _next_payload(source_job, next_type)
    step = next_type.value.lower()
    key = f"preview-{project.id}-{step}-{source_job.id}"

    try:
        job = jobs_svc.enqueue_job(
            db,
            user=user,
            project=project,
            job_type=next_type,
            idempotency_key=key,
            payload=payload,
        )
        logger.info(
            "preview_chain next=%s job_id=%s from=%s project=%s",
            next_type.value,
            job.id,
            source_job.id,
            project.id,
        )
        return job
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        failed = Job(
            project_id=project.id,
            type=next_type.value,
            status=JobStatus.FAILED.value,
            provider=jobs_svc.PROVIDER_BY_TYPE.get(next_type),
            idempotency_key=key,
            request_id=source_job.request_id,
            cost_credits=0,
            error=detail[:2000],
            result={"payload": payload},
        )
        db.add(failed)
        db.commit()
        logger.warning(
            "preview_chain blocked next=%s project=%s: %s",
            next_type.value,
            project.id,
            detail,
        )
        return failed
