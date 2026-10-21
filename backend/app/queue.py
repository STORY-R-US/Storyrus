"""Notificacao de jobs via Redis.

O banco continua sendo a fonte da verdade (estado, idempotencia, retry). O Redis
serve apenas para *acordar* o worker quase instantaneamente, evitando latencia do
polling. Se o Redis estiver indisponivel, tudo degrada para polling do banco — o
pipeline nao para.
"""

from __future__ import annotations

import logging
import uuid
from functools import lru_cache

from app.config import settings

logger = logging.getLogger("queue")

_PENDING_LIST = "stories:jobs:pending"


@lru_cache
def _redis():
    try:
        import redis  # import tardio

        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=1)
        client.ping()
        return client
    except Exception as exc:  # noqa: BLE001 - sem Redis -> fallback para polling
        logger.warning("Redis indisponivel (%s); usando polling do banco", exc)
        return None


def notify(job_id: uuid.UUID) -> None:
    """Sinaliza que ha um job novo (best-effort)."""
    client = _redis()
    if client is None:
        return
    try:
        client.rpush(_PENDING_LIST, str(job_id))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falha ao notificar Redis: %s", exc)


def wait(timeout_s: float) -> bool:
    """Bloqueia ate ~timeout_s aguardando sinal. Retorna True se acordou por sinal.

    Em fallback (sem Redis) retorna False imediatamente; o caller deve dormir.
    """
    client = _redis()
    if client is None:
        return False
    try:
        item = client.blpop(_PENDING_LIST, timeout=int(max(1, timeout_s)))
        return item is not None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falha no blpop Redis: %s", exc)
        return False
