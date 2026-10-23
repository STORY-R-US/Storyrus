"""Dependencies compartilhadas.

Rotas autenticadas exigem o session token do Clerk. A linha local é resolvida
por `clerk_user_id` ou, no primeiro acesso, pelo e-mail. Mutações de livro
exigem conta registrada e e-mail verificado via require_registered_user.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import is_guest_user
from app.services.clerk_identity import user_from_bearer

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None or not creds.credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nao autenticado")
    return user_from_bearer(creds.credentials, db)


def require_registered_user(user: User = Depends(get_current_user)) -> User:
    """Bloqueia convidados e contas com e-mail nao verificado."""
    if is_guest_user(email=user.email, password_hash=user.password_hash):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cadastro necessario")
    if user.email_verified_at is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Confirme seu e-mail")
    return user


def require_adult_user(user: User = Depends(require_registered_user)) -> User:
    """Serviço para pais e responsáveis. A criança não opera o estúdio."""
    if user.adult_confirmed_at is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Confirme que voce tem 18 anos ou mais",
        )
    return user
