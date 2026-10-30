"""Orquestracao de jobs: enfileirar etapas pesadas de forma idempotente.

Regras (do documento de arquitetura):
- Com credits_enabled, a etapa debita creditos ANTES de enfileirar.
- Com o sistema de creditos desligado (padrao), o custo da etapa e zero.
- Idempotency-Key evita duplicar job/custo: repetir a chamada retorna o job existente.
- Limite de jobs simultaneos por usuario (backpressure).
- Em SQLite/dev nao ha broker; expomos `enqueue_fn` para o worker real (RQ/Celery/Temporal).
"""

import logging
import uuid
from collections.abc import Callable

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import DataError, IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Job, JobStatus, JobType, Project, User
from app.observability.context import get_request_id
from app.services import credits, spend_guard

logger = logging.getLogger(__name__)

# Custo (em creditos) por tipo de etapa.
COST_BY_TYPE: dict[JobType, int] = {
    JobType.AVATAR: settings.cost_avatar_credits,
    JobType.REALISTIC: settings.cost_avatar_credits,
    JobType.STORY: settings.cost_story_credits,
    JobType.EBOOK: settings.cost_ebook_credits,
    JobType.STORYBOARD: settings.cost_avatar_credits,
    JobType.VIDEO: settings.cost_video_credits,
    JobType.NARRATED_VIDEO: settings.cost_narrated_video_credits,
    JobType.EXTRA_CHARACTER: settings.cost_avatar_credits,
}

PROVIDER_BY_TYPE: dict[JobType, str] = {
    JobType.AVATAR: settings.image_provider,
    JobType.REALISTIC: settings.image_provider,
    JobType.STORY: settings.text_provider,
    JobType.EBOOK: "internal",
    JobType.STORYBOARD: settings.image_provider,
    JobType.VIDEO: settings.video_provider,
    JobType.NARRATED_VIDEO: "ffmpeg+tts",
    JobType.EXTRA_CHARACTER: settings.image_provider,
}

# Hook de enfileiramento no broker real. Default: no-op (worker faz polling de PENDING).
enqueue_fn: Callable[[uuid.UUID], None] = lambda job_id: None


def _json_value(value: object) -> object:
    """Payload persistível em JSON/Postgres (sem NUL nem surrogate solto)."""
    if isinstance(value, str):
        return value.replace("\x00", "").encode("utf-8", "replace").decode("utf-8")
    if isinstance(value, dict):
        return {str(_json_value(key)): _json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return _json_value(str(value))


def _clean_key(value: str | None, limit: int) -> str | None:
    if not value:
        return None
    cleaned = str(_json_value(value)).strip()
    return cleaned[:limit] or None


def _active_jobs(db: Session, user: User, *, exclude_job_id: uuid.UUID | None = None) -> int:
    """Conta jobs ativos (PENDING/RUNNING) para o limite de backpressure.

    Inclui VIDEO / NARRATED_VIDEO — mesmo padrão dos demais tipos — para evitar
    pile-up de jobs longos sem teto de concorrência.
    """
    stmt = (
        select(func.count(Job.id))
        .join(Project, Project.id == Job.project_id)
        .where(
            Project.user_id == user.id,
            Job.status.in_([JobStatus.PENDING.value, JobStatus.RUNNING.value]),
        )
    )
    if exclude_job_id is not None:
        stmt = stmt.where(Job.id != exclude_job_id)
    return db.scalar(stmt) or 0


def enqueue_job(
    db: Session,
    *,
    user: User,
    project: Project,
    job_type: JobType,
    idempotency_key: str | None = None,
    payload: dict | None = None,
    completing_job: Job | None = None,
) -> Job:
    """Cria (ou retorna) um job, debitando creditos atomicamente.

    Tudo numa transacao: idempotencia -> backpressure -> debito -> insert.
    Blip de conexão retenta uma vez. Corrida de chave e falha de refresh
    devolvem o job já gravado — não viram HTTP 500.
    """
    from app.services.privacy import require_photo_authorization

    require_photo_authorization(db, project.id)
    key = _clean_key(idempotency_key, 255)
    safe_payload = _json_value(payload) if payload else None
    if safe_payload is not None and not isinstance(safe_payload, dict):
        safe_payload = {"value": safe_payload}

    last_operational: OperationalError | None = None
    for attempt in range(2):
        try:
            return _enqueue_job_once(
                db,
                user=user,
                project=project,
                job_type=job_type,
                idempotency_key=key,
                payload=safe_payload,
                completing_job=completing_job,
            )
        except OperationalError as exc:
            last_operational = exc
            db.rollback()
            logger.warning("enqueue operational error attempt=%s: %s", attempt + 1, exc)
    assert last_operational is not None
    raise last_operational


def _enqueue_job_once(
    db: Session,
    *,
    user: User,
    project: Project,
    job_type: JobType,
    idempotency_key: str | None,
    payload: dict | None,
    completing_job: Job | None = None,
) -> Job:
    # 1) Idempotencia: mesma chave -> mesmo job (sem novo custo).
    if idempotency_key:
        existing = db.scalar(select(Job).where(Job.idempotency_key == idempotency_key))
        if existing is not None:
            return existing

    cost = COST_BY_TYPE.get(job_type, 0) if settings.credits_enabled else 0
    if (project.book_profile or {}).get("test_mode"):
        cost = 0

    # 2) Backpressure por usuario.
    # The next preview step replaces the step that just finished its work.
    # Counting both would block an already accepted book when the queue is full.
    exclude_id = (
        completing_job.id
        if completing_job is not None and completing_job.project_id == project.id
        else None
    )
    if _active_jobs(db, user, exclude_job_id=exclude_id) >= settings.max_concurrent_jobs_per_user:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Há {settings.max_concurrent_jobs_per_user} gerações em andamento na sua conta. "
            "Aguarde uma delas terminar e tente novamente.",
        )

    # 3) Teto diario da plataforma (USD/creditos) ANTES do vendor (STO-18).
    try:
        spend_guard.assert_can_enqueue(db, job_type.value, cost_credits=cost)
    except spend_guard.SpendCeilingError as exc:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, str(exc))

    # 4) Debito ANTES da etapa paga.
    try:
        credits.debit(db, user.id, cost)
    except credits.InsufficientCreditsError as exc:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    # 5) Persiste o job PENDING (request_id da request HTTP para correlacao).
    request_id = get_request_id()
    job = Job(
        project_id=project.id,
        type=job_type.value,
        status=JobStatus.PENDING.value,
        provider=_clean_key(PROVIDER_BY_TYPE.get(job_type), 32),
        idempotency_key=idempotency_key,
        request_id=request_id,
        cost_credits=cost,
        result={"payload": payload} if payload else None,
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        # Corrida com a mesma Idempotency-Key: devolve o job que ganhou o insert.
        return _job_after_conflict(db, idempotency_key)
    except DataError as exc:
        db.rollback()
        logger.exception("enqueue data error job_type=%s", job_type.value)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Não foi possível iniciar esta etapa. Tente de novo.",
        ) from exc
    job = _refreshed_job(db, job, idempotency_key)
    logger.info(
        "enqueued job_type=%s job_id=%s project_id=%s",
        job.type,
        job.id,
        job.project_id,
    )
    # 6) Sinaliza o broker (best-effort).
    try:
        enqueue_fn(job.id)
    except Exception:  # noqa: BLE001 - broker indisponivel nao deve quebrar a request
        pass
    try:
        from app.workers.api_pump import kick

        kick()
    except Exception:  # noqa: BLE001 - a fila no banco segue se o pump nao acordar
        logger.exception("kick do pump falhou job_id=%s", job.id)
    return job


def _job_after_conflict(db: Session, idempotency_key: str | None) -> Job:
    db.rollback()
    if idempotency_key:
        existing = db.scalar(select(Job).where(Job.idempotency_key == idempotency_key))
        if existing is not None:
            logger.info(
                "idempotent race job_id=%s key=%s",
                existing.id,
                idempotency_key,
            )
            return existing
    raise HTTPException(
        status.HTTP_409_CONFLICT,
        "Não foi possível iniciar esta etapa agora. Tente de novo.",
    )


def _refreshed_job(db: Session, job: Job, idempotency_key: str | None) -> Job:
    try:
        db.refresh(job)
    except Exception:  # noqa: BLE001 - insert já commitou; refresh não pode virar 500
        # O insert já commitou. Refresh quebrado não pode virar 500.
        logger.exception("refresh apos enqueue falhou key=%s", idempotency_key)
        db.rollback()
        if idempotency_key:
            existing = db.scalar(select(Job).where(Job.idempotency_key == idempotency_key))
            if existing is not None:
                return existing
        raise
    return job


def mark_failed_and_refund(db: Session, job: Job, error: str) -> None:
    """Estado FAILED definitivo + estorno de creditos (compensacao)."""
    project = db.get(Project, job.project_id)
    job.status = JobStatus.FAILED.value
    job.error = error[:2000]
    if job.cost_credits and project is not None:
        credits.refund(db, project.user_id, job.cost_credits)
    from app.services.error_report import record_error

    record_error(
        db,
        message=job.error,
        project_id=job.project_id,
        job_id=job.id,
        stage=job.type,
    )
    db.commit()
