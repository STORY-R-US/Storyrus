"""Explicit approval gates and sequential page generation for the Studio."""

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_registered_user
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
    user: User = Depends(require_registered_user),
    db: Session = Depends(get_db),
):
    project = _project(db, user, project_id)
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
    user: User = Depends(require_registered_user),
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
