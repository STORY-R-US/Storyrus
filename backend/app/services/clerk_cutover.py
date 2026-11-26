"""Troca da instância do Clerk (desenvolvimento → produção) sem perder contas.

Os ids de usuário mudam entre instâncias do Clerk e não existe transferência
direta. Sem este mapa, quem já usa o site daria 409 ("Esta conta já está
ligada a outro acesso") no primeiro login depois da troca das chaves.

Ordem:
1. `plan`: conta o que será feito. Não chama o Clerk.
2. `stage`: com a chave sk_live_ em CLERK_PRODUCTION_SECRET_KEY, cria na
   produção uma conta por e-mail verificado, com `external_id = users.id`, e
   grava o par no mapa. Nenhum login atual muda.
3. Troca das chaves (CLERK_SECRET_KEY sk_live_ no Render, publishable key na
   Vercel). No primeiro login, a conta de produção mapeada assume o vínculo
   (`claim_mapped_user`). O users.id, os livros, os pedidos e os créditos ficam.
4. `rollback`: devolve cada vínculo ao id antigo, se for preciso voltar às
   chaves de desenvolvimento.

A ligação vem do mapa explícito, não de coincidência de e-mail. A única
exceção é a conta que nunca verificou o e-mail (`pending_email`): ela não é
criada na produção e só religa quando alguém entra lá com esse e-mail já
verificado pelo Clerk.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import ClerkAccountMap, User
from app.security import is_guest_user

logger = logging.getLogger(__name__)

_CLERK_API = "https://api.clerk.com/v1"
_LIVE_PREFIX = "sk_live_"
# Endereços de teste da suíte e do painel; não são caixas de e-mail reais.
_SKIP_DOMAINS = ("@example.com", "@storyrus.app")

STAGED = "staged"
ACTIVE = "active"
PENDING_EMAIL = "pending_email"
ACTIVE_EMAIL = "active_email"
CONFLICT = "conflict"
ROLLED_BACK = "rolled_back"


def live_instance() -> bool:
    """A API já confere os logins na instância de produção do Clerk."""
    return (settings.clerk_secret_key or "").strip().startswith(_LIVE_PREFIX)


def production_key() -> str:
    """Chave da produção: a de preparo ou, depois da troca, a própria do login."""
    staged = (settings.clerk_production_secret_key or "").strip()
    if staged.startswith(_LIVE_PREFIX):
        return staged
    current = (settings.clerk_secret_key or "").strip()
    return current if current.startswith(_LIVE_PREFIX) else ""


def _mask(email: str) -> str:
    name, _, domain = email.partition("@")
    if not domain:
        return "***"
    return f"{name[:2]}***@{domain}"


def _real_account(user: User) -> bool:
    if is_guest_user(email=user.email, password_hash=user.password_hash):
        return False
    email = (user.email or "").strip().lower()
    return bool(email) and not email.endswith(_SKIP_DOMAINS)


@dataclass
class CutoverPlan:
    live_instance: bool
    production_key_ready: bool
    accounts: int = 0
    skipped_test_or_guest: int = 0
    to_create: int = 0
    to_mark_pending_email: int = 0
    unverified_without_login: int = 0
    by_status: dict[str, int] = field(default_factory=dict)
    conflicts: list[dict[str, str]] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "live_instance": self.live_instance,
            "production_key_ready": self.production_key_ready,
            "accounts": self.accounts,
            "skipped_test_or_guest": self.skipped_test_or_guest,
            "to_create": self.to_create,
            "to_mark_pending_email": self.to_mark_pending_email,
            "unverified_without_login": self.unverified_without_login,
            "by_status": self.by_status,
            "conflicts": self.conflicts,
        }


def _needs_stage(user: User, row: ClerkAccountMap, *, retry_conflicts: bool) -> bool:
    """Linha já gravada que ainda pede preparo."""
    if row.status == CONFLICT:
        return retry_conflicts
    # Depois de um rollback, o próximo preparo arma a linha de novo.
    if row.status == ROLLED_BACK:
        return True
    # Conta que verificou o e-mail depois do primeiro preparo.
    return row.status == PENDING_EMAIL and user.email_verified_at is not None


def _rows_by_user(db: Session) -> dict:
    return {row.user_id: row for row in db.scalars(select(ClerkAccountMap))}


def plan(db: Session) -> CutoverPlan:
    """O que `stage` faria agora. Só lê o banco."""
    result = CutoverPlan(live_instance=live_instance(), production_key_ready=bool(production_key()))
    rows = _rows_by_user(db)
    for row in rows.values():
        result.by_status[row.status] = result.by_status.get(row.status, 0) + 1
        if row.status == CONFLICT:
            user = db.get(User, row.user_id)
            result.conflicts.append(
                {
                    "user_id": str(row.user_id),
                    "email": _mask(user.email if user else ""),
                    "note": row.note or "",
                }
            )
    for user in db.scalars(select(User).order_by(User.created_at)):
        if not _real_account(user):
            result.skipped_test_or_guest += 1
            continue
        result.accounts += 1
        row = rows.get(user.id)
        if row is not None and not _needs_stage(user, row, retry_conflicts=False):
            continue
        if user.email_verified_at is not None:
            result.to_create += 1
        elif user.clerk_user_id:
            result.to_mark_pending_email += 1
        else:
            result.unverified_without_login += 1
    return result


def _request(method: str, path: str, *, params=None, payload=None) -> httpx.Response:
    key = production_key()
    if not key:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Falta a chave sk_live_ da produção do Clerk (CLERK_PRODUCTION_SECRET_KEY).",
        )
    return httpx.request(
        method,
        f"{_CLERK_API}{path}",
        headers={"Authorization": f"Bearer {key}"},
        params=params,
        json=payload,
        timeout=15.0,
    )


class RateLimited(Exception):
    pass


def _checked(response: httpx.Response) -> httpx.Response:
    if response.status_code == 429:
        raise RateLimited()
    if response.status_code >= 400:
        logger.warning("clerk_cutover_http status=%s", response.status_code)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"O Clerk de produção respondeu {response.status_code}.",
        )
    return response


def _production_users_with_email(email: str) -> list[dict]:
    response = _checked(_request("GET", "/users", params={"email_address": [email], "limit": 10}))
    body = response.json()
    if isinstance(body, dict):
        body = body.get("data") or []
    return list(body or [])


def _create_production_user(user: User) -> str:
    response = _checked(
        _request(
            "POST",
            "/users",
            payload={
                "external_id": str(user.id),
                "email_address": [user.email.strip().lower()],
                "skip_password_requirement": True,
                "skip_legal_checks": True,
            },
        )
    )
    created = str(response.json().get("id") or "")
    if not created.startswith("user_"):
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "O Clerk não devolveu o id da conta.")
    return created


def _stage_one(db: Session, user: User, row: ClerkAccountMap | None) -> str:
    if row is None:
        row = ClerkAccountMap(user_id=user.id, dev_clerk_user_id=user.clerk_user_id)
    if user.email_verified_at is None:
        row.status = PENDING_EMAIL
        row.prod_clerk_user_id = None
        row.note = "E-mail nunca verificado: não foi criado na produção."
        db.add(row)
        db.commit()
        return PENDING_EMAIL
    found = _production_users_with_email(user.email.strip().lower())
    mine = next((item for item in found if item.get("external_id") == str(user.id)), None)
    if mine is not None:
        prod_id = str(mine.get("id") or "")
    elif found:
        row.status = CONFLICT
        row.prod_clerk_user_id = None
        row.note = "Já existe conta na produção com esse e-mail e sem este external_id."
        db.add(row)
        db.commit()
        return CONFLICT
    else:
        prod_id = _create_production_user(user)
    row.prod_clerk_user_id = prod_id
    row.status = STAGED
    row.note = None
    db.add(row)
    db.commit()
    return STAGED


def stage(db: Session, *, limit: int = 50, retry_conflicts: bool = False) -> dict:
    """Cria na produção as contas que faltam, `limit` por chamada. Repetível.

    Conflitos só são tentados de novo com `retry_conflicts` (depois de conferir
    à mão a conta que já existia na produção).
    """
    if not production_key():
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Falta a chave sk_live_ da produção do Clerk (CLERK_PRODUCTION_SECRET_KEY).",
        )
    rows = _rows_by_user(db)
    done: dict[str, int] = {}
    processed = 0
    rate_limited = False
    for user in db.scalars(select(User).order_by(User.created_at)).all():
        if processed >= limit:
            break
        if not _real_account(user):
            continue
        row = rows.get(user.id)
        if row is not None and not _needs_stage(user, row, retry_conflicts=retry_conflicts):
            continue
        if user.email_verified_at is None and not user.clerk_user_id:
            continue
        try:
            outcome = _stage_one(db, user, row)
        except RateLimited:
            db.rollback()
            rate_limited = True
            break
        done[outcome] = done.get(outcome, 0) + 1
        processed += 1
        time.sleep(0.05)
    remaining = plan(db)
    return {
        "processed": processed,
        "result": done,
        "rate_limited": rate_limited,
        "remaining": remaining.to_create + remaining.to_mark_pending_email,
        "plan": remaining.as_dict(),
    }


def claim_mapped_user(db: Session, *, clerk_user_id: str, email: str, email_verified: bool):
    """Primeiro login na produção: passa o vínculo da conta mapeada. Sem commit.

    Só age com a chave de produção no ar: antes disso, um id de produção nem
    chega aqui, porque o token não confere nas chaves da instância de dev.
    """
    if not live_instance():
        return None
    row = db.scalar(
        select(ClerkAccountMap).where(
            ClerkAccountMap.prod_clerk_user_id == clerk_user_id,
            ClerkAccountMap.status == STAGED,
        )
    )
    if row is not None:
        user = db.get(User, row.user_id)
        if user is None:
            return None
        user.clerk_user_id = clerk_user_id
        row.status = ACTIVE
        row.activated_at = datetime.now(UTC)
        db.add(row)
        logger.info("clerk_cutover_claim user_id=%s", user.id)
        return user
    if not email_verified or not email:
        return None
    user = db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))
    if user is None:
        return None
    row = db.scalar(
        select(ClerkAccountMap).where(
            ClerkAccountMap.user_id == user.id,
            ClerkAccountMap.status == PENDING_EMAIL,
        )
    )
    if row is None or row.dev_clerk_user_id != user.clerk_user_id:
        return None
    user.clerk_user_id = clerk_user_id
    row.prod_clerk_user_id = clerk_user_id
    row.status = ACTIVE_EMAIL
    row.activated_at = datetime.now(UTC)
    db.add(row)
    logger.info("clerk_cutover_claim_email user_id=%s", user.id)
    return user


def rollback(db: Session) -> dict:
    """Volta os vínculos ativados ao id antigo (para voltar às chaves de dev)."""
    restored = 0
    for row in db.scalars(
        select(ClerkAccountMap).where(ClerkAccountMap.status.in_([ACTIVE, ACTIVE_EMAIL]))
    ).all():
        user = db.get(User, row.user_id)
        if user is None:
            continue
        user.clerk_user_id = row.dev_clerk_user_id
        # Não volta a `staged`: com a chave de produção ainda no ar, o próximo
        # login assumiria a conta de novo. Só um novo `stage` arma a linha.
        row.status = ROLLED_BACK
        row.activated_at = None
        db.add_all([user, row])
        restored += 1
    db.commit()
    from app.services.clerk_identity import reset_profile_cache

    reset_profile_cache()
    return {"restored": restored, "plan": plan(db).as_dict()}


def staged_production_id(db: Session, user_id) -> str | None:
    """Conta de produção ainda não assumida (para apagar junto com a local)."""
    row = db.scalar(select(ClerkAccountMap).where(ClerkAccountMap.user_id == user_id))
    if row is None or row.status != STAGED:
        return None
    return row.prod_clerk_user_id


def delete_production_user(prod_clerk_user_id: str) -> None:
    """Apaga a conta criada no preparo. Falha só vai para o log."""
    if settings.app_env == "test" or not production_key():
        return
    try:
        response = _request("DELETE", f"/users/{prod_clerk_user_id}")
        if response.status_code not in (200, 404):
            logger.warning("clerk_cutover_delete status=%s", response.status_code)
    except httpx.HTTPError:
        logger.exception("clerk_cutover_delete_failed")
