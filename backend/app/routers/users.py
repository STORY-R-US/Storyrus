"""Painel de usuarios cadastrados. Mesma senha dos paineis de gastos/pedidos."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Project, User
from app.owner_auth import require_owner_password
from app.schemas import OwnerUserOut, OwnerUsersOut, OwnerUserUpdateIn

router = APIRouter(prefix="/v1/users", tags=["users"])

_GUEST_HASH = "!guest"


def _project_count(db: Session, user_id: uuid.UUID) -> int:
    return int(db.scalar(select(func.count(Project.id)).where(Project.user_id == user_id)) or 0)


def _to_out(db: Session, user: User, project_count: int | None = None) -> OwnerUserOut:
    return OwnerUserOut(
        id=user.id,
        email=user.email,
        credits=user.credits,
        created_at=user.created_at,
        project_count=_project_count(db, user.id) if project_count is None else project_count,
        full_name=user.full_name,
        phone=user.phone,
        email_verified=user.email_verified_at is not None,
        postal_code=user.postal_code,
        street=user.street,
        number=user.number,
        complement=user.complement,
        district=user.district,
        city=user.city,
        state=user.state,
        country=user.country,
        terms_accepted_at=user.terms_accepted_at,
    )


def _registered_user(db: Session, user_id: uuid.UUID) -> User:
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None or user.password_hash == _GUEST_HASH:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario nao encontrado")
    return user


@router.get("", response_model=OwnerUsersOut)
def list_users(
    _: Annotated[None, Depends(require_owner_password)],
    db: Annotated[Session, Depends(get_db)],
) -> OwnerUsersOut:
    """Lista contas cadastradas (exclui convidados), mais recentes primeiro."""
    project_count = (
        select(func.count(Project.id))
        .where(Project.user_id == User.id)
        .correlate(User)
        .scalar_subquery()
        .label("project_count")
    )
    rows = db.execute(
        select(User, project_count)
        .where(User.password_hash != _GUEST_HASH)
        .order_by(User.created_at.desc())
    ).all()

    users = [_to_out(db, user, int(count or 0)) for user, count in rows]
    return OwnerUsersOut(total=len(users), users=users)


@router.get("/{user_id}", response_model=OwnerUserOut)
def get_user(
    user_id: uuid.UUID,
    _: Annotated[None, Depends(require_owner_password)],
    db: Annotated[Session, Depends(get_db)],
) -> OwnerUserOut:
    return _to_out(db, _registered_user(db, user_id))


@router.patch("/{user_id}", response_model=OwnerUserOut)
def update_user(
    user_id: uuid.UUID,
    body: OwnerUserUpdateIn,
    _: Annotated[None, Depends(require_owner_password)],
    db: Annotated[Session, Depends(get_db)],
) -> OwnerUserOut:
    user = _registered_user(db, user_id)
    data = body.model_dump(exclude_unset=True)

    if "email" in data and data["email"] is not None:
        email = str(data["email"]).strip().lower()
        clash = db.scalar(select(User).where(func.lower(User.email) == email, User.id != user.id))
        if clash is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "E-mail ja cadastrado")
        user.email = email

    if "credits" in data and data["credits"] is not None:
        user.credits = int(data["credits"])

    if "email_verified" in data and data["email_verified"] is not None:
        if data["email_verified"]:
            if user.email_verified_at is None:
                user.email_verified_at = datetime.now(UTC)
            user.email_verify_token_hash = None
        else:
            user.email_verified_at = None

    for key in (
        "full_name",
        "phone",
        "postal_code",
        "street",
        "number",
        "complement",
        "district",
        "city",
        "state",
        "country",
    ):
        if key in data:
            setattr(user, key, data[key])

    db.add(user)
    db.commit()
    db.refresh(user)
    return _to_out(db, user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: uuid.UUID,
    _: Annotated[None, Depends(require_owner_password)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Apaga a conta cadastrada e os projetos ligados a ela."""
    user = _registered_user(db, user_id)
    # Carrega filhos para o cascade ORM apagar projetos/vozes no SQLite.
    _ = user.projects
    _ = user.voices
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
