"""Acesso aos paineis admin (gastos, pedidos, usuarios).

Aceita JWT de conta com `users.is_admin` (ou e-mail em `OWNER_EMAILS`, que
promove `is_admin` no primeiro acesso). A senha compartilhada
(`X-Usage-Password`) só entra se `OWNER_PASSWORD_FALLBACK` estiver ligado.
"""

from __future__ import annotations

import hmac
import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import rate_limit
from app.config import settings
from app.database import get_db
from app.models import User
from app.security import decode_access_token, is_guest_user

HEADER = "X-Usage-Password"
_bearer = HTTPBearer(auto_error=False)


def accepted_passwords() -> list[str]:
    """Senha atual + anterior (rotacao). Ordem: atual primeiro."""
    out: list[str] = []
    for raw in (
        settings.usage_dashboard_password,
        settings.usage_dashboard_password_previous,
    ):
        cleaned = (raw or "").strip()
        if cleaned and cleaned not in out:
            out.append(cleaned)
    return out


# Conta do dono. Continua válida mesmo se OWNER_EMAILS no Render vier vazio
# e apagar o default — senão o painel pede a senha compartilhada para sempre.
BUILTIN_OWNER_EMAILS = frozenset({"eng.andrevitor89@gmail.com"})


def owner_emails() -> set[str]:
    """E-mails do dono (minusculos) que entram com a sessão do estúdio."""
    found = set(BUILTIN_OWNER_EMAILS)
    raw = (settings.owner_emails or "").strip()
    if raw:
        found.update(part.strip().lower() for part in raw.split(",") if part.strip())
    return found


def password_matches(provided: str, accepted: list[str]) -> bool:
    provided_b = provided.encode("utf-8")
    matched = False
    for expected in accepted:
        expected_b = expected.encode("utf-8")
        if len(provided_b) == len(expected_b) and hmac.compare_digest(provided_b, expected_b):
            matched = True
    return matched


_GMAIL_DOMAINS = frozenset({"gmail.com", "googlemail.com"})


def _fold_gmail(email: str) -> str | None:
    """Gmail ignora pontos e o sufixo +etiqueta. Os dois domínios são a mesma caixa."""
    if "@" not in email:
        return None
    local, domain = email.rsplit("@", 1)
    if domain not in _GMAIL_DOMAINS:
        return None
    local = local.split("+", 1)[0].replace(".", "")
    return f"{local}@gmail.com"


def is_owner_email(email: str | None) -> bool:
    if not email:
        return False
    normalized = email.strip().lower()
    owners = owner_emails()
    if normalized in owners:
        return True
    folded = _fold_gmail(normalized)
    if folded is None:
        return False
    return any(_fold_gmail(owner) == folded for owner in owners)


def promote_verified_owner(user: User) -> bool:
    """Marca is_admin quando o e-mail já verificado é do dono."""
    if user.is_admin or user.email_verified_at is None:
        return False
    if not is_owner_email(user.email):
        return False
    user.is_admin = True
    return True


def user_is_admin(user: User) -> bool:
    """Conta verificada com papel de admin, ou e-mail listado em OWNER_EMAILS."""
    if is_guest_user(email=user.email, password_hash=user.password_hash):
        return False
    if user.email_verified_at is None:
        return False
    if user.is_admin:
        return True
    return is_owner_email(user.email)


def _admin_from_bearer(
    creds: HTTPAuthorizationCredentials | None,
    db: Session,
) -> User | None:
    if creds is None:
        return None
    payload = decode_access_token(creds.credentials)
    if not payload or "sub" not in payload:
        return None
    try:
        user_id = uuid.UUID(payload["sub"])
    except ValueError:
        return None
    user = db.get(User, user_id)
    if user is None or not user_is_admin(user):
        return None
    if promote_verified_owner(user):
        db.add(user)
        db.commit()
    return user


def require_owner_password(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    x_usage_password: Annotated[str | None, Header(alias=HEADER)] = None,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> None:
    accepted = accepted_passwords()
    owners = owner_emails()
    fallback = bool(settings.owner_password_fallback)

    ip = rate_limit.client_ip(request)
    lock_key = f"usage:fail:{ip}"
    max_attempts = int(settings.usage_lockout_max_attempts)
    window = float(settings.usage_lockout_window_s)

    # Conta admin (JWT) — não conta para lockout de senha.
    if _admin_from_bearer(creds, db) is not None:
        rate_limit.clear_key(lock_key)
        return

    if not fallback:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Acesso restrito a administradores")

    if not accepted and not owners:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Painel de gastos nao configurado",
        )

    provided = (x_usage_password or "").strip()
    # Senha correta sempre libera, mesmo durante lockout (evita trancar o dono).
    if accepted and password_matches(provided, accepted):
        rate_limit.clear_key(lock_key)
        return

    if not accepted:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Senha invalida")

    if rate_limit.blocked(lock_key, max_attempts, window):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Muitas tentativas; tente mais tarde",
        )

    rate_limit.hit(lock_key, window)
    if rate_limit.blocked(lock_key, max_attempts, window):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Muitas tentativas; tente mais tarde",
        )
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Senha invalida")
