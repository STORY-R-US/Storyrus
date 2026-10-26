"""Aprovação de personagem e livro."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_adult_user
from app.models import Project, User, _now
from app.schemas import ProjectOut
from app.services import book_profile

from .common import get_owned_project

router = APIRouter()


@router.post("/{project_id}/avatar/approve", response_model=ProjectOut)
def approve_avatar(
    project_id: uuid.UUID,
    user: User = Depends(require_adult_user),
    db: Session = Depends(get_db),
) -> Project:
    project = get_owned_project(db, user, project_id)
    book_profile.require_stage(project, "avatar_ready", "avatar_approved")
    if not project.character_ref:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Gere o personagem antes de aprovar")
    project.character_approved_at = _now()
    if book_profile.enabled(project):
        book_profile.update(project, stage="avatar_approved")
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/book/approve", response_model=ProjectOut)
def approve_book(
    project_id: uuid.UUID,
    user: User = Depends(require_adult_user),
    db: Session = Depends(get_db),
) -> Project:
    project = get_owned_project(db, user, project_id)
    book_profile.require_stage(project, "book_ready")
    if not project.character_approved_at:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Aprove o personagem antes do livro")
    if not project.ebook_url:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Monte o e-book antes de aprovar o livro")
    flow = project.purchase_flow or {}
    if flow.get("preview_ready_at"):
        from app.printkit.service import get_print_order, prepare_files
        from app.services import purchase_flow

        order = get_print_order(db, project.id)
        if not flow.get("full_book_ready_at") or not order or order.payment_status != "paid":
            raise HTTPException(409, "Revise o livro completo após a confirmação do pagamento.")
        if purchase_flow.active_job(db, project):
            raise HTTPException(409, "Aguarde a geração do livro completo terminar.")
        purchase_flow.update(project, stage="production_approved")
        project.book_approved_at = _now()
        prepare_files(db, project, order)
        db.commit()
        db.refresh(project)
        try:
            from app.services.transactional_email import notify_print_shop

            notify_print_shop(db, project, order)
        except Exception:
            import logging

            logging.getLogger(__name__).exception("print_shop_email_failed code=%s", order.code)
        return project
    project.book_approved_at = _now()
    db.commit()
    db.refresh(project)
    return project
