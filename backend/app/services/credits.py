"""Servico de creditos: debito antes de etapa paga e estorno em falha.

Usa bloqueio de linha (SELECT ... FOR UPDATE) no Postgres para evitar corrida
ao debitar/estornar. Em SQLite (testes) o lock e ignorado silenciosamente.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


class InsufficientCreditsError(Exception):
    def __init__(self, required: int, available: int):
        self.required = required
        self.available = available
        super().__init__(f"Creditos insuficientes: requer {required}, disponivel {available}")


def _lock_user(db: Session, user_id: uuid.UUID) -> User:
    stmt = select(User).where(User.id == user_id)
    if db.bind.dialect.name == "postgresql":
        stmt = stmt.with_for_update()
    user = db.scalar(stmt)
    if user is None:
        raise ValueError("Usuario nao encontrado")
    return user


def debit(db: Session, user_id: uuid.UUID, amount: int) -> int:
    """Debita `amount` creditos. Levanta InsufficientCreditsError se faltar.

    Nao faz commit: o caller decide a transacao (ex.: debita e enfileira no
    mesmo commit atomico).
    """
    if amount <= 0:
        return _lock_user(db, user_id).credits
    user = _lock_user(db, user_id)
    if user.credits < amount:
        raise InsufficientCreditsError(amount, user.credits)
    user.credits -= amount
    db.flush()
    return user.credits


def refund(db: Session, user_id: uuid.UUID, amount: int) -> int:
    """Estorna creditos (ex.: job FAILED apos esgotar retries)."""
    if amount <= 0:
        return _lock_user(db, user_id).credits
    user = _lock_user(db, user_id)
    user.credits += amount
    db.flush()
    return user.credits


def grant(db: Session, user_id: uuid.UUID, amount: int) -> int:
    """Concede creditos (compra/bonus)."""
    return refund(db, user_id, amount)
