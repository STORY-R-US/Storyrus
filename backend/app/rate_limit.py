"""Rate limiting leve (guest auth e similares).

Memoria em processo por padrao; se Redis estiver up, usa INCR+EXPIRE para
compartilhar o contador entre instancias da API.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque

from app.config import settings

logger = logging.getLogger("rate_limit")

_lock = threading.Lock()
_windows: dict[str, deque[float]] = defaultdict(deque)


def reset() -> None:
    """Zera o contador em memoria (testes)."""
    with _lock:
        _windows.clear()


def _prune(bucket: deque[float], now: float, window_s: float) -> None:
    cutoff = now - window_s
    while bucket and bucket[0] < cutoff:
        bucket.popleft()


def _allow_memory(key: str, limit: int, window_s: float) -> bool:
    if limit <= 0:
        return True
    now = time.monotonic()
    with _lock:
        bucket = _windows[key]
        _prune(bucket, now, window_s)
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


def _allow_redis(key: str, limit: int, window_s: float) -> bool | None:
    """True/False se Redis respondeu; None se indisponivel (cai p/ memoria)."""
    if limit <= 0:
        return True
    try:
        from app import queue

        client = queue._redis()
        if client is None:
            return None
        rkey = f"stories:rl:{key}"
        count = client.incr(rkey)
        if count == 1:
            client.expire(rkey, int(max(1, window_s)))
        return int(count) <= limit
    except Exception as exc:  # noqa: BLE001
        logger.warning("rate limit Redis falhou (%s); usando memoria", exc)
        return None


def allow(key: str, limit: int, window_s: float) -> bool:
    """Consome 1 unidade do bucket. False = acima do limite."""
    redis_ok = _allow_redis(key, limit, window_s)
    if redis_ok is not None:
        return redis_ok
    return _allow_memory(key, limit, window_s)


def _blocked_memory(key: str, limit: int, window_s: float) -> bool:
    if limit <= 0:
        return False
    now = time.monotonic()
    with _lock:
        bucket = _windows[key]
        _prune(bucket, now, window_s)
        return len(bucket) >= limit


def _blocked_redis(key: str, limit: int) -> bool | None:
    """True/False se Redis respondeu; None se indisponivel."""
    if limit <= 0:
        return False
    try:
        from app import queue

        client = queue._redis()
        if client is None:
            return None
        raw = client.get(f"stories:rl:{key}")
        if raw is None:
            return False
        return int(raw) >= limit
    except Exception as exc:  # noqa: BLE001
        logger.warning("rate limit Redis peek falhou (%s); usando memoria", exc)
        return None


def blocked(key: str, limit: int, window_s: float) -> bool:
    """True se o bucket ja esta no limite (sem consumir)."""
    redis_ok = _blocked_redis(key, limit)
    if redis_ok is not None:
        return redis_ok
    return _blocked_memory(key, limit, window_s)


def hit(key: str, window_s: float) -> None:
    """Registra 1 evento na janela (ex. falha de senha)."""
    # limit alto: so queremos INCR/append, nao rejeitar aqui.
    allow(key, limit=10**9, window_s=window_s)


def clear_key(key: str) -> None:
    """Zera o bucket (ex. senha correta apos tentativas)."""
    try:
        from app import queue

        client = queue._redis()
        if client is not None:
            client.delete(f"stories:rl:{key}")
    except Exception as exc:  # noqa: BLE001
        logger.warning("rate limit Redis clear falhou (%s)", exc)
    with _lock:
        _windows.pop(key, None)


def client_ip(request) -> str:
    """IP efetivo: X-Forwarded-For (primeiro) ou peer do socket."""
    forwarded = request.headers.get("x-forwarded-for") or ""
    if forwarded.strip():
        return forwarded.split(",")[0].strip()[:128]
    if request.client and request.client.host:
        return request.client.host[:128]
    return "unknown"


def check_guest(request) -> None:
    """Levanta HTTP 429 se IP (e fingerprint, se houver) estourarem o limite."""
    from fastapi import HTTPException, status

    window = float(settings.guest_rate_limit_window_s)
    ip = client_ip(request)
    if not allow(f"guest:ip:{ip}", settings.guest_rate_limit_per_ip, window):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Muitos convidados deste IP; tente mais tarde",
        )

    fp = (
        request.headers.get("x-device-fingerprint")
        or request.headers.get("x-client-fingerprint")
        or ""
    ).strip()
    if fp:
        fp = fp[:128]
        if not allow(
            f"guest:fp:{fp}",
            settings.guest_rate_limit_per_fingerprint,
            window,
        ):
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Muitos convidados deste dispositivo; tente mais tarde",
            )


def check_password_reset(request, *, email: str) -> None:
    """Limita pedidos de redefinição por IP e por e-mail."""
    from fastapi import HTTPException, status

    window = float(settings.password_reset_rate_limit_window_s)
    ip = client_ip(request)
    if not allow(
        f"pwreset:ip:{ip}",
        settings.password_reset_rate_limit_per_ip,
        window,
    ):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Muitos pedidos deste IP; tente mais tarde",
        )
    email_key = (email or "").strip().lower()[:255]
    if email_key and not allow(
        f"pwreset:email:{email_key}",
        settings.password_reset_rate_limit_per_email,
        window,
    ):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Muitos pedidos para este e-mail; tente mais tarde",
        )
