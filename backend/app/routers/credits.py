"""Saldo e concessao de creditos (compra/bonus)."""

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import CreditGrantIn, CreditsOut
from app.services import credits as credits_svc

router = APIRouter(prefix="/v1/credits", tags=["credits"])

_UNSAFE_GRANT_SECRETS = frozenset({"", "change-me", "change-me-in-prod", "change-me-webhook"})


def _grant_secret_ok(provided: str | None) -> bool:
    secret = (settings.credit_grant_secret or "").strip()
    if secret in _UNSAFE_GRANT_SECRETS:
        return False
    if not provided:
        return False
    return hmac.compare_digest(secret, provided)


@router.get("", response_model=CreditsOut)
def balance(user: User = Depends(get_current_user)) -> CreditsOut:
    return CreditsOut(credits=user.credits)


@router.post("/grant", response_model=CreditsOut)
def grant(
    body: CreditGrantIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_admin_secret: str | None = Header(default=None, alias="X-Admin-Secret"),
) -> CreditsOut:
    if not _grant_secret_ok(x_admin_secret):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Grant desabilitado")
    new_balance = credits_svc.grant(db, user.id, body.amount)
    db.commit()
    return CreditsOut(credits=new_balance)
