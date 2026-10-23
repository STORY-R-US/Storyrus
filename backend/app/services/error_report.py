"""Relatório dos erros do ensaio. Cada falha fica registrada e visível."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job, Project, UsageEvent


def record_error(
    db: Session,
    *,
    message: str,
    project_id: uuid.UUID | None,
    job_id: uuid.UUID | None = None,
    stage: str = "",
) -> None:
    text = (message or "").strip()
    if not text or project_id is None:
        return
    db.add(
        UsageEvent(
            project_id=project_id,
            job_id=job_id,
            kind="error",
            provider="ensaio",
            action="failure",
            label=(stage or "erro")[:32],
            meta={"message": text[:2000], "stage": (stage or "")[:80]},
        )
    )


def recent_errors(db: Session, *, limit: int = 40) -> list[dict]:
    """Falhas novas do relatório e jobs que já terminaram em FAILED."""
    items: list[dict] = []
    seen: set[tuple[str, str]] = set()
    events = db.scalars(
        select(UsageEvent)
        .where(UsageEvent.kind == "error")
        .order_by(UsageEvent.created_at.desc())
        .limit(limit)
    ).all()
    projects = (
        {
            project.id: project
            for project in db.scalars(
                select(Project).where(Project.id.in_([event.project_id for event in events]))
            ).all()
        }
        if events
        else {}
    )
    for event in events:
        meta = event.meta if isinstance(event.meta, dict) else {}
        message = str(meta.get("message") or event.label)
        key = (str(event.project_id), message)
        if key in seen:
            continue
        seen.add(key)
        project = projects.get(event.project_id)
        items.append(
            {
                "created_at": event.created_at,
                "project_id": event.project_id,
                "child_name": project.child_name if project else None,
                "stage": str(meta.get("stage") or event.label),
                "message": message,
            }
        )
    if len(items) < limit:
        jobs = db.scalars(
            select(Job)
            .where(Job.status == "FAILED", Job.error.is_not(None))
            .order_by(Job.created_at.desc())
            .limit(limit)
        ).all()
        extra_projects = (
            {
                project.id: project
                for project in db.scalars(
                    select(Project).where(Project.id.in_([job.project_id for job in jobs]))
                ).all()
            }
            if jobs
            else {}
        )
        for job in jobs:
            message = (job.error or "").strip()
            key = (str(job.project_id), message)
            if not message or key in seen:
                continue
            seen.add(key)
            project = extra_projects.get(job.project_id)
            items.append(
                {
                    "created_at": job.created_at,
                    "project_id": job.project_id,
                    "child_name": project.child_name if project else None,
                    "stage": job.type,
                    "message": message,
                }
            )
    items.sort(key=lambda item: item["created_at"], reverse=True)
    return items[:limit]
