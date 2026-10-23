"""Perfil da conta. Identidade (e-mail, senha, verificação) fica no Clerk."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_registered_user
from app.models import User
from app.owner_auth import user_is_admin
from app.schemas import ProfileUpdateIn, UserOut
from app.security import is_guest_user

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def _user_out(user: User) -> UserOut:
    guest = is_guest_user(email=user.email, password_hash=user.password_hash)
    admin = user_is_admin(user)
    return UserOut(
        id=user.id,
        email=user.email,
        credits=user.credits,
        created_at=user.created_at,
        is_guest=guest,
        email_verified=guest or user.email_verified_at is not None,
        is_admin=admin,
        is_owner=admin,
        full_name=user.full_name,
        phone=user.phone,
        postal_code=user.postal_code,
        street=user.street,
        number=user.number,
        complement=user.complement,
        district=user.district,
        city=user.city,
        state=user.state,
        country=user.country,
        terms_accepted_at=user.terms_accepted_at,
        adult_confirmed_at=user.adult_confirmed_at,
    )


def _apply_profile(user: User, body: ProfileUpdateIn) -> None:
    data = body.model_dump(exclude_unset=True)
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
    if data.get("accept_terms"):
        user.terms_accepted_at = datetime.now(UTC)
    if data.get("confirm_adult"):
        user.adult_confirmed_at = datetime.now(UTC)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return _user_out(user)


@router.patch("/me", response_model=UserOut)
def update_me(
    body: ProfileUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_registered_user),
) -> UserOut:
    _apply_profile(user, body)
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_out(user)
