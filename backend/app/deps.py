"""Dependencies compartilhadas.

Rotas autenticadas exigem JWT. Convidados passam por POST /v1/auth/guest,
que cria um usuario isolado e devolve o token — nunca um guest compartilhado.
Mutacoes de livro exigem conta registrada via require_registered_user.
"""

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import decode_access_token, is_guest_user

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nao autenticado")
    payload = decode_access_token(creds.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nao autenticado")
    try:
        user_id = uuid.UUID(payload["sub"])
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nao autenticado") from exc
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nao autenticado")
    return user


def require_registered_user(user: User = Depends(get_current_user)) -> User:
    """Bloqueia convidados e contas com e-mail nao verificado."""
    if is_guest_user(email=user.email, password_hash=user.password_hash):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cadastro necessario")
    if user.email_verified_at is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Confirme seu e-mail")
    return user
