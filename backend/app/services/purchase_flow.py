"""Customer approvals, payment gate and one full book generation per order."""

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Job, JobStatus, JobType, Project, _now


def update(project: Project, **values) -> None:
    project.purchase_flow = {**(project.purchase_flow or {}), **values}


def timestamp() -> str:
    return _now().isoformat()


def active_job(db: Session, project: Project) -> bool:
    return bool(
        db.scalar(
            select(Job.id)
            .where(
                Job.project_id == project.id,
                Job.status.in_([JobStatus.PENDING.value, JobStatus.RUNNING.value]),
            )
            .limit(1)
        )
    )


def require_unpaid(db: Session, project: Project) -> None:
    from app.printkit.service import get_print_order

    order = get_print_order(db, project.id)
    if order and order.payment_status in {"paid", "pending"}:
        raise HTTPException(
            409, "O pedido já está em pagamento ou produção. Solicite ajustes na revisão final."
        )


def require_paid(db: Session, project: Project) -> None:
    from app.services import book_profile

    book_profile.require_real_preview(project)
    if book_profile.enabled(project) and not (project.purchase_flow or {}).get("preview_approved_at"):
        raise HTTPException(409, "Aprove a prévia antes de continuar o livro.")
    if not (project.purchase_flow or {}).get("preview_ready_at"):
        return
    from app.printkit.service import get_print_order

    order = get_print_order(db, project.id)
    if not order or order.payment_status != "paid":
        raise HTTPException(
            409, "O pedido está em cotação. A produção começa após confirmar o pagamento."
        )


def reset_preview(project: Project, *, force: bool = False) -> None:
    if not force and not (project.purchase_flow or {}).get("stage"):
        return
    update(
        project,
        preview_ready_at=None,
        preview_approved_at=None,
        full_book_ready_at=None,
        quoted_at=None,
        stage="preview_generating",
    )


def enqueue_paid_book(db: Session, order, *, retry: bool = False) -> Job:
    from app.services import jobs
    from app.services.book_profile import require_real_preview

    project = order.project

    require_real_preview(project)
    flow = project.purchase_flow or {}
    if order.payment_status != "paid" or not flow.get("preview_approved_at"):
        raise ValueError("Confirme o pagamento e aprove a prévia antes de gerar o livro completo.")
    # A fixed server key also deduplicates repeated payment callbacks.
    key = f"purchase-book-{order.id}-{flow.get('book_revision', 0)}"
    existing = db.scalar(
        select(Job)
        .where(or_(Job.idempotency_key == key, Job.idempotency_key.startswith(key + "-retry-")))
        .order_by(Job.created_at.desc())
        .limit(1)
    )
    if existing and not (retry and existing.status == JobStatus.FAILED.value):
        return existing
    if existing:
        # Concurrent retries share the failed job's id as a deterministic key.
        # A fresh job retains the normal debit/refund behavior when credits are enabled.
        key += f"-retry-{existing.id}"
    project.book_approved_at = None
    update(project, stage="generating_book")
    return jobs.enqueue_job(
        db,
        user=project.user,
        project=project,
        job_type=_paid_book_type(project),
        idempotency_key=key,
        payload={"purchase_full_book": True},
    )


def _paid_book_type(project: Project):
    profile = project.book_profile or {}
    if profile.get("version") != 1:
        return JobType.EBOOK
    if profile.get("stories") and profile.get("stage") in {"story_approved", "preview_approved"}:
        return JobType.AVATAR
    return JobType.STORY
