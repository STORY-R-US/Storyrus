"""Aprovação de personagem e livro."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_registered_user
from app.models import Project, User, _now
from app.schemas import ProjectOut

from .common import get_owned_project

router = APIRouter()


@router.post("/{project_id}/avatar/approve", response_model=ProjectOut)
def approve_avatar(
    project_id: uuid.UUID,
    user: User = Depends(require_registered_user),
    db: Session = Depends(get_db),
) -> Project:
    project = get_owned_project(db, user, project_id)
    if not project.character_ref:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Gere o personagem antes de aprovar")
    project.character_approved_at = _now()
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/book/approve", response_model=ProjectOut)
def approve_book(
    project_id: uuid.UUID,
    user: User = Depends(require_registered_user),
    db: Session = Depends(get_db),
) -> Project:
    project = get_owned_project(db, user, project_id)
    if not project.character_approved_at:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Aprove o personagem antes do livro")
    if not project.ebook_url:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Monte o e-book antes de aprovar o livro")
    project.book_approved_at = _now()
    db.commit()
    db.refresh(project)
    return project
