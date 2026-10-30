"""Reviewable cleanup of abandoned projects. Paid orders require separate review."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models import Asset, Job, PrintOrder, Project

UNPAID_RETENTION_DAYS = 90


def retention_candidates(db, *, days: int, now: datetime | None = None, project_id=None) -> list:
    if days < 1:
        raise ValueError("O prazo deve ser positivo")
    cutoff = (now or datetime.now(UTC)) - timedelta(days=days)
    candidates = []
    query = select(Project).where(Project.created_at < cutoff)
    if project_id is not None:
        query = query.where(Project.id == project_id)
    for project in db.scalars(query):
        order = db.scalar(select(PrintOrder).where(PrintOrder.project_id == project.id))
        if order and order.payment_status in {"paid", "pending"}:
            continue
        jobs = db.scalars(select(Job).where(Job.project_id == project.id)).all()
        if any(job.status in {"PENDING", "RUNNING"} for job in jobs):
            continue
        dates = [project.created_at] + [job.updated_at for job in jobs]
        if project.last_accessed_at:
            dates.append(project.last_accessed_at)
        dates.extend(db.scalars(select(Asset.created_at).where(Asset.project_id == project.id)))
        if order:
            dates.append(order.updated_at)
        if all(
            (date.replace(tzinfo=UTC) if date.tzinfo is None else date) < cutoff for date in dates
        ):
            candidates.append(project)
    return candidates


def cleanup_abandoned_projects() -> int:
    import logging

    from app.database import SessionLocal
    from app.routers.projects.common import purge_project

    removed = 0
    with SessionLocal() as db:
        ids = [project.id for project in retention_candidates(db, days=UNPAID_RETENTION_DAYS)]
        for pid in ids:
            try:
                locked = db.scalar(
                    select(Project)
                    .where(Project.id == pid)
                    .with_for_update(skip_locked=True)
                    .execution_options(populate_existing=True)
                )
                if locked is None:
                    db.rollback()
                    continue
                db.scalar(select(PrintOrder).where(PrintOrder.project_id == pid).with_for_update())
                if retention_candidates(db, days=UNPAID_RETENTION_DAYS, project_id=pid):
                    purge_project(db, pid)
                    db.commit()
                    removed += 1
                else:
                    db.commit()
            except Exception:
                db.rollback()
                logging.getLogger(__name__).exception("privacy_retention_failed project=%s", pid)
    return removed


async def retention_loop() -> None:
    import asyncio
    import logging

    await asyncio.sleep(60)
    while True:
        try:
            await asyncio.to_thread(cleanup_abandoned_projects)
        except Exception:
            logging.getLogger(__name__).exception("privacy_retention_cycle_failed")
        await asyncio.sleep(24 * 60 * 60)
