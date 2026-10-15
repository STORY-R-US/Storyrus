"""Hashing de senha e emissao/validacao de JWT."""

import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import unquote

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def create_access_token(subject: str, extra: dict | None = None) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_min),
        **(extra or {}),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_email_verify_token(subject: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "purpose": "email_verify",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=settings.email_verify_ttl_min),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def new_email_verify_secret() -> str:
    """Token curto, sem pontos — cabe no link do e-mail sem quebrar."""
    return secrets.token_urlsafe(32)


def new_password_reset_secret() -> str:
    """Token curto para link de redefinição (mesmo formato do verify)."""
    return secrets.token_urlsafe(32)


def normalize_verify_token(raw: str | None) -> str:
    """Remove quebra de linha / encoding de cliente de e-mail."""
    if not raw:
        return ""
    token = unquote(str(raw).strip().strip("<>"))
    return re.sub(r"\s+", "", token)


def create_password_reset_token(subject: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "purpose": "password_reset",
        "iat": now,
        "exp": now + timedelta(minutes=settings.password_reset_ttl_min),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


def decode_email_verify_token(token: str) -> dict | None:
    payload = decode_access_token(token)
    if not payload or payload.get("purpose") != "email_verify" or "sub" not in payload:
        return None
    return payload


def decode_password_reset_token(token: str) -> dict | None:
    payload = decode_access_token(token)
    if not payload or payload.get("purpose") != "password_reset" or "sub" not in payload:
        return None
    return payload


def hash_token(raw: str) -> str:
    """Hash estável para guardar o token de verificação no banco."""
    import hashlib

    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def decode_access_token_allow_expired(token: str) -> dict | None:
    """Valida assinatura/alg sem exigir `exp` (STO-26 resume de sessao)."""
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": False},
        )
    except JWTError:
        return None


def is_guest_user(*, email: str, password_hash: str) -> bool:
    """Convidados: hash sentinela `!guest` + e-mail sintetico @storyrus.app."""
    return password_hash == "!guest" and email.endswith("@storyrus.app")
