"""Helpers compartilhados pelo router de projetos."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Job, JobType, Project, User
from app.schemas import JobAcceptedOut


def get_owned_project(db: Session, user: User, project_id: uuid.UUID) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Projeto nao encontrado")
    return project


def accept_job(job: Job) -> JobAcceptedOut:
    return JobAcceptedOut(
        job_id=job.id,
        status=job.status,
        type=JobType(job.type),
        estimated_cost_credits=job.cost_credits,
        request_id=job.request_id,
    )
