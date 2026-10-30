"""Helpers compartilhados pelo router de projetos."""

from __future__ import annotations

import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import storage
from app.models import Asset, Job, JobType, OrderTicket, PrintOrder, Project, UsageEvent, User
from app.owner_auth import user_is_admin
from app.schemas import JobAcceptedOut

logger = logging.getLogger(__name__)


def get_owned_project(db: Session, user: User, project_id: uuid.UUID) -> Project:
    """O dono do livro abre o próprio projeto. O admin abre o de qualquer conta."""
    project = db.get(Project, project_id)
    if project is None or (project.user_id != user.id and not user_is_admin(user)):
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
    if db.scalar(
        select(Job.id)
        .where(Job.project_id == project_id, Job.status.in_(["PENDING", "RUNNING"]))
        .limit(1)
    ):
        raise HTTPException(
            409,
            "A geração ainda está em andamento. Aguarde o término ou solicite a interrupção pelo contato de privacidade antes de excluir.",
        )
    keys: list[str] = []
    if project is not None:
        for asset in db.scalars(select(Asset).where(Asset.project_id == project_id)):
            _remember(keys, asset.storage_key)
            _remember(keys, (asset.meta or {}).get("watermark_key"))
        ref = project.character_ref or {}
        if isinstance(ref, dict):
            _remember(keys, ref.get("storage_key"))
        for field in ("ebook_url", "video_url", "narrated_video_url"):
            value = getattr(project, field, None)
            if isinstance(value, str) and value.startswith(f"projects/{project_id}/"):
                _remember(keys, value)
        extras = project.extra_characters or []
        if isinstance(extras, list):
            for item in extras:
                if isinstance(item, dict):
                    _remember(keys, item.get("storage_key"))
                    _remember(keys, item.get("character_storage_key"))
        printed = db.scalar(select(PrintOrder).where(PrintOrder.project_id == project_id))
        if printed is not None:
            _remember(keys, printed.cover_key)
            _remember(keys, printed.interior_key)
    # Keep the database records if storage cleanup fails: a retry must still
    # know which objects to delete, rather than reporting a false success.
    try:
        for key in set(keys):
            storage.delete_key(key)
        storage.delete_project_objects(project_id)
    except Exception as exc:
        logger.exception("storage: exclusão incompleta do projeto %s", project_id)
        raise HTTPException(503, "Não foi possível concluir a exclusão. Tente novamente.") from exc
    for stmt in (
        delete(UsageEvent).where(UsageEvent.project_id == project_id),
        delete(Asset).where(Asset.project_id == project_id),
        delete(OrderTicket).where(OrderTicket.project_id == project_id),
        delete(PrintOrder).where(PrintOrder.project_id == project_id),
        delete(Job).where(Job.project_id == project_id),
        delete(Project).where(Project.id == project_id),
    ):
        db.execute(stmt.execution_options(synchronize_session=False))


def accept_job(job: Job) -> JobAcceptedOut:
    return JobAcceptedOut(
        job_id=job.id,
        status=job.status,
        type=JobType(job.type),
        estimated_cost_credits=job.cost_credits,
        request_id=job.request_id,
    )
