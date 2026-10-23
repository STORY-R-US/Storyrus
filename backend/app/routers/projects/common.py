"""Helpers compartilhados pelo router de projetos."""

from __future__ import annotations

import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import storage
from app.models import Asset, Job, JobType, OrderTicket, PrintOrder, Project, UsageEvent, User
from app.schemas import JobAcceptedOut

logger = logging.getLogger(__name__)


def get_owned_project(db: Session, user: User, project_id: uuid.UUID) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Projeto nao encontrado")
    return project


def _remember(keys: list[str], value: object) -> None:
    if isinstance(value, str) and value.strip():
        keys.append(value)


def purge_project(db: Session, project_id: uuid.UUID) -> None:
    """Apaga o projeto, os registros filhos e os arquivos guardados.

    O SQL direto evita diferença de cascade entre o SQLite dos testes e o
    Postgres. A exclusão do arquivo não desfaz o apagamento do projeto.
    """
    project = db.get(Project, project_id)
    keys: list[str] = []
    if project is not None:
        keys.extend(
            db.scalars(select(Asset.storage_key).where(Asset.project_id == project_id)).all()
        )
        ref = project.character_ref or {}
        if isinstance(ref, dict):
            _remember(keys, ref.get("storage_key"))
        extras = project.extra_characters or []
        if isinstance(extras, list):
            for item in extras:
                if isinstance(item, dict):
                    _remember(keys, item.get("storage_key"))
        printed = db.scalar(select(PrintOrder).where(PrintOrder.project_id == project_id))
        if printed is not None:
            _remember(keys, printed.cover_key)
            _remember(keys, printed.interior_key)
    for stmt in (
        delete(UsageEvent).where(UsageEvent.project_id == project_id),
        delete(Asset).where(Asset.project_id == project_id),
        delete(OrderTicket).where(OrderTicket.project_id == project_id),
        delete(PrintOrder).where(PrintOrder.project_id == project_id),
        delete(Job).where(Job.project_id == project_id),
        delete(Project).where(Project.id == project_id),
    ):
        db.execute(stmt.execution_options(synchronize_session=False))
    for key in keys:
        try:
            storage.delete_key(key)
        except Exception:
            logger.exception("storage: falha ao apagar %s do projeto %s", key, project_id)


def accept_job(job: Job) -> JobAcceptedOut:
    return JobAcceptedOut(
        job_id=job.id,
        status=job.status,
        type=JobType(job.type),
        estimated_cost_credits=job.cost_credits,
        request_id=job.request_id,
    )
