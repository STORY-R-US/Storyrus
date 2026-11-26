"""Painel admin da troca da instância do Clerk (desenvolvimento → produção).

Só conta admin. Nenhuma rota mostra chave nem e-mail completo.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.owner_auth import require_owner_password
from app.services import clerk_cutover

router = APIRouter(
    prefix="/v1/admin/clerk-cutover",
    tags=["admin"],
    dependencies=[Depends(require_owner_password)],
)


class RollbackIn(BaseModel):
    confirm: str = ""


@router.get("")
def cutover_plan(db: Annotated[Session, Depends(get_db)]) -> dict:
    """O que falta preparar. Só lê o banco."""
    return clerk_cutover.plan(db).as_dict()


@router.post("/stage")
def cutover_stage(
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    retry_conflicts: bool = False,
) -> dict:
    """Cria na produção do Clerk as contas que faltam. Pode repetir."""
    return clerk_cutover.stage(db, limit=limit, retry_conflicts=retry_conflicts)


@router.post("/rollback")
def cutover_rollback(body: RollbackIn, db: Annotated[Session, Depends(get_db)]) -> dict:
    """Devolve os vínculos ao id antigo. Exige confirm = "VOLTAR"."""
    if body.confirm != "VOLTAR":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Envie confirm = "VOLTAR".')
    return clerk_cutover.rollback(db)
