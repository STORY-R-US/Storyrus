"""Sessão do Clerk → linha local em `users`.

O `users.id` (UUID) continua dono de projetos, créditos e pedidos. O token do
Clerk só identifica a pessoa. No primeiro acesso, um e-mail já cadastrado e
ainda sem `clerk_user_id` reaproveita essa linha. Contas convidadas não entram
nessa ligação.

Fora de `APP_ENV=test` o Bearer é um session token RS256, conferido nas chaves
do Clerk. O e-mail vem da Backend API, não de um claim do token. Em teste, o
conftest emite um Bearer HS256 com `purpose=clerk_test`; esse atalho não existe
em dev, staging ou prod.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User
from app.owner_auth import promote_verified_owner
from app.security import is_guest_user

logger = logging.getLogger(__name__)

CLERK_PASSWORD_HASH = "!clerk"
_CLERK_API = "https://api.clerk.com/v1"
_JWKS_TTL_S = 600.0
_TEST_PURPOSE = "clerk_test"
_jwks_cache: tuple[float, list[dict]] | None = None


@dataclass(frozen=True)
class ClerkIdentity:
    clerk_user_id: str
    email: str
    email_verified: bool


def reset_jwks_cache() -> None:
    global _jwks_cache
    _jwks_cache = None


def _norm_email(value: str) -> str:
    return str(value).strip().lower()


def _b64url_uint(data: str) -> int:
    pad = "=" * (-len(data) % 4)
    raw = base64.urlsafe_b64decode(data + pad)
    return int.from_bytes(raw, "big")


def _jwk_to_pem(jwk: dict) -> str:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers

    public = RSAPublicNumbers(_b64url_uint(jwk["e"]), _b64url_uint(jwk["n"])).public_key()
    return public.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")


def fetch_jwks() -> list[dict]:
    """Chaves públicas da instância. Cache curto para não ir à rede em todo request."""
    global _jwks_cache
    now = time.monotonic()
    if _jwks_cache is not None and now - _jwks_cache[0] < _JWKS_TTL_S:
        return _jwks_cache[1]
    response = httpx.get(
        f"{_CLERK_API}/jwks",
        headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
        timeout=10.0,
    )
    response.raise_for_status()
    keys = list(response.json().get("keys") or [])
    _jwks_cache = (now, keys)
    return keys


def _clerk_error(response: httpx.Response) -> str:
    try:
        errors = response.json().get("errors") or []
    except Exception:
        errors = []
    if errors:
        message = str(errors[0].get("long_message") or errors[0].get("message") or "").strip()
        if message:
            return message
    return "O Clerk recusou a alteração."


def _clerk_json(method: str, path: str, payload: dict) -> dict:
    if not (settings.clerk_secret_key or "").strip():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "O Clerk não está configurado.")
    response = httpx.request(
        method,
        f"{_CLERK_API}{path}",
        headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
        json=payload,
        timeout=15.0,
    )
    if response.status_code >= 400:
        code = status.HTTP_400_BAD_REQUEST if response.status_code < 500 else status.HTTP_502_BAD_GATEWAY
        raise HTTPException(code, _clerk_error(response))
    return response.json() if response.content else {}


def set_clerk_password(clerk_user_id: str, password: str) -> None:
    """Troca a senha de login e encerra as outras sessões dessa conta."""
    _clerk_json(
        "PATCH",
        f"/users/{clerk_user_id}",
        {
            "password": password,
            "skip_password_checks": False,
            "sign_out_of_other_sessions": True,
        },
    )


def set_clerk_email(clerk_user_id: str, email: str) -> None:
    """Inclui o e-mail como verificado e principal no Clerk."""
    _clerk_json(
        "POST",
        "/email_addresses",
        {
            "user_id": clerk_user_id,
            "email_address": email,
            "verified": True,
            "primary": True,
        },
    )


def fetch_clerk_user(user_id: str) -> dict:
    response = httpx.get(
        f"{_CLERK_API}/users/{user_id}",
        headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json()


def primary_email(user: dict) -> tuple[str, bool]:
    emails = list(user.get("email_addresses") or [])
    primary_id = user.get("primary_email_address_id")
    chosen = next((item for item in emails if item.get("id") == primary_id), None)
    if chosen is None and emails:
        chosen = emails[0]
    address = (chosen or {}).get("email_address") or ""
    if not str(address).strip():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nao autenticado")
    verified = ((chosen or {}).get("verification") or {}).get("status") == "verified"
    return _norm_email(str(address)), verified


def create_test_session_token(
    *,
    clerk_user_id: str,
    email: str,
    email_verified: bool = True,
) -> str:
    """Bearer da suíte. Recusado quando APP_ENV não é test."""
    if settings.app_env != "test":
        raise RuntimeError("Token de teste só existe com APP_ENV=test")
    now = datetime.now(UTC)
    payload = {
        "sub": clerk_user_id,
        "email": _norm_email(email),
        "email_verified": email_verified,
        "purpose": _TEST_PURPOSE,
        "iat": now,
        "exp": now + timedelta(hours=12),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _identity_from_test_token(token: str) -> ClerkIdentity | None:
    if settings.app_env != "test":
        return None
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    if payload.get("purpose") != _TEST_PURPOSE or "sub" not in payload or "email" not in payload:
        return None
    return ClerkIdentity(
        clerk_user_id=str(payload["sub"]),
        email=_norm_email(str(payload["email"])),
        email_verified=bool(payload.get("email_verified")),
    )


def _identity_from_clerk_jwt(token: str) -> ClerkIdentity:
    if not (settings.clerk_secret_key or "").strip():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nao autenticado")
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nao autenticado") from exc
    kid = header.get("kid")
    try:
        keys = fetch_jwks()
    except httpx.HTTPError as exc:
        logger.warning("clerk_jwks_unavailable")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nao autenticado") from exc
    match = next((item for item in keys if item.get("kid") == kid), None)
    if match is None:
        reset_jwks_cache()
        try:
            keys = fetch_jwks()
        except httpx.HTTPError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nao autenticado") from exc
        match = next((item for item in keys if item.get("kid") == kid), None)
    if match is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nao autenticado")
    try:
        payload = jwt.decode(
            token,
            _jwk_to_pem(match),
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nao autenticado") from exc
    sub = str(payload.get("sub") or "")
    if not sub.startswith("user_"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nao autenticado")
    try:
        profile = fetch_clerk_user(sub)
    except httpx.HTTPError as exc:
        logger.warning("clerk_user_unavailable sub=%s", sub)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nao autenticado") from exc
    email, verified = primary_email(profile)
    return ClerkIdentity(clerk_user_id=sub, email=email, email_verified=verified)


def verify_session_token(token: str) -> ClerkIdentity:
    tested = _identity_from_test_token(token)
    if tested is not None:
        return tested
    if settings.app_env == "test":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nao autenticado")
    return _identity_from_clerk_jwt(token)


def _mark_verified(user: User, identity: ClerkIdentity) -> None:
    if identity.email_verified and user.email_verified_at is None:
        user.email_verified_at = datetime.now(UTC)


def _save(db: Session, user: User) -> User:
    promote_verified_owner(user)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Esta conta ja esta ligada a outro acesso",
        ) from exc
    db.refresh(user)
    return user


def resolve_local_user(db: Session, identity: ClerkIdentity) -> User:
    """Acha, liga pelo e-mail ou cria a linha local. Não reatribui um id já gravado."""
    linked = db.scalar(select(User).where(User.clerk_user_id == identity.clerk_user_id))
    if linked is not None:
        _mark_verified(linked, identity)
        return _save(db, linked)

    existing = db.scalar(select(User).where(func.lower(User.email) == identity.email))
    if existing is not None:
        if is_guest_user(email=existing.email, password_hash=existing.password_hash):
            raise HTTPException(status.HTTP_409_CONFLICT, "E-mail ja cadastrado")
        if existing.clerk_user_id and existing.clerk_user_id != identity.clerk_user_id:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Esta conta ja esta ligada a outro acesso",
            )
        existing.clerk_user_id = identity.clerk_user_id
        _mark_verified(existing, identity)
        return _save(db, existing)

    now = datetime.now(UTC)
    created = User(
        email=identity.email,
        password_hash=CLERK_PASSWORD_HASH,
        clerk_user_id=identity.clerk_user_id,
        credits=settings.signup_bonus_credits,
        email_verified_at=now if identity.email_verified else None,
    )
    db.add(created)
    try:
        promote_verified_owner(created)
        db.commit()
    except IntegrityError:
        db.rollback()
        again = db.scalar(select(User).where(User.clerk_user_id == identity.clerk_user_id))
        if again is None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Esta conta ja esta ligada a outro acesso",
            ) from None
        return again
    db.refresh(created)
    return created


def linked_user(db: Session, identity: ClerkIdentity) -> User | None:
    """Conta já ligada a este Clerk. Não cria linha nem reatribui e-mail.

    O painel admin usa isto: um Bearer de conta apagada não pode recriar a
    pessoa só porque a rota também aceita senha de dono.
    """
    user = db.scalar(select(User).where(User.clerk_user_id == identity.clerk_user_id))
    if user is None:
        return None
    _mark_verified(user, identity)
    return _save(db, user)


def user_from_bearer(token: str, db: Session) -> User:
    return resolve_local_user(db, verify_session_token(token))


def _secret_bytes(secret: str) -> bytes:
    raw = secret.strip()
    if raw.startswith("whsec_"):
        raw = raw[len("whsec_") :]
    pad = "=" * (-len(raw) % 4)
    return base64.b64decode(raw + pad)


def verify_svix(
    *,
    secret: str,
    body: bytes,
    svix_id: str | None,
    svix_timestamp: str | None,
    svix_signature: str | None,
) -> str | None:
    """None se a assinatura Svix confere. Caso contrário, a mensagem de erro."""
    if not secret.strip():
        return "Webhook do Clerk nao configurado"
    if not svix_id or not svix_timestamp or not svix_signature:
        return "Assinatura ausente"
    try:
        stamped = int(svix_timestamp)
    except ValueError:
        return "Assinatura invalida"
    if abs(int(time.time()) - stamped) > 300:
        return "Assinatura expirada"
    try:
        key = _secret_bytes(secret)
    except (ValueError, binascii.Error):
        return "Assinatura invalida"
    signed = f"{svix_id}.{svix_timestamp}.".encode() + body
    expected = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
    presented = [
        part[3:]
        for part in svix_signature.split()
        if part.startswith("v1,") and len(part) > 3
    ]
    if not presented:
        return "Assinatura invalida"
    if not any(
        len(item) == len(expected) and hmac.compare_digest(item, expected) for item in presented
    ):
        return "Assinatura invalida"
    return None


def apply_clerk_event(db: Session, event_type: str, data: dict) -> None:
    """`user.updated` troca o e-mail local. `user.deleted` só zera o vínculo."""
    clerk_user_id = str(data.get("id") or "")
    if not clerk_user_id:
        return
    user = db.scalar(select(User).where(User.clerk_user_id == clerk_user_id))
    if user is None or is_guest_user(email=user.email, password_hash=user.password_hash):
        return
    if event_type == "user.deleted":
        user.clerk_user_id = None
        db.add(user)
        db.commit()
        return
    if event_type != "user.updated":
        return
    try:
        email, verified = primary_email(data)
    except HTTPException:
        return
    if email != user.email.lower():
        clash = db.scalar(
            select(User).where(func.lower(User.email) == email, User.id != user.id)
        )
        if clash is not None:
            logger.warning("clerk_email_conflict clerk_user_id=%s", clerk_user_id)
        else:
            user.email = email
    if verified and user.email_verified_at is None:
        user.email_verified_at = datetime.now(UTC)
        promote_verified_owner(user)
    db.add(user)
    db.commit()
