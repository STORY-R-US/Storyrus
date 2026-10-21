"""Assinatura HMAC de webhooks com anti-replay (timestamp + nonce).

Formato do payload assinado (UTF-8 + corpo bruto):

    {timestamp}.{nonce}.{raw_body}

Headers esperados no callback:

- ``X-Timestamp`` — Unix epoch em segundos (int)
- ``X-Nonce`` — string opaca unica (ex. UUID)
- ``X-Signature`` — HMAC-SHA256 hex do payload acima

Rejeita timestamp fora da janela ``webhook_max_age_s`` e nonce ja visto
(Redis SET NX quando disponivel; senao memoria no processo).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import threading
import time

from app.config import settings

logger = logging.getLogger("webhook_auth")

_lock = threading.Lock()
# nonce -> expires_at (monotonic)
_seen: dict[str, float] = {}


def reset() -> None:
    """Zera nonces em memoria (testes)."""
    with _lock:
        _seen.clear()


def canonical_message(timestamp: str, nonce: str, body: bytes) -> bytes:
    return f"{timestamp}.{nonce}.".encode("utf-8") + body


def sign(secret: str, timestamp: str, nonce: str, body: bytes) -> str:
    """HMAC-SHA256 hex do payload canonico."""
    return hmac.new(
        secret.encode("utf-8"),
        canonical_message(timestamp, nonce, body),
        hashlib.sha256,
    ).hexdigest()


def _prune_memory(now: float) -> None:
    expired = [n for n, exp in _seen.items() if exp <= now]
    for n in expired:
        del _seen[n]


def _claim_nonce_memory(nonce: str, ttl_s: float) -> bool:
    now = time.monotonic()
    with _lock:
        _prune_memory(now)
        if nonce in _seen:
            return False
        _seen[nonce] = now + ttl_s
        return True


def _claim_nonce_redis(nonce: str, ttl_s: float) -> bool | None:
    """True/False se Redis respondeu; None se indisponivel."""
    try:
        from app import queue

        client = queue._redis()
        if client is None:
            return None
        rkey = f"stories:webhook:nonce:{nonce}"
        # SET NX: so o primeiro claim ganha.
        ok = client.set(rkey, "1", nx=True, ex=max(1, int(ttl_s)))
        return bool(ok)
    except Exception as exc:  # noqa: BLE001
        logger.warning("nonce Redis falhou (%s); usando memoria", exc)
        return None


def claim_nonce(nonce: str, ttl_s: float | None = None) -> bool:
    """Marca o nonce como usado. False = replay."""
    ttl = float(ttl_s if ttl_s is not None else settings.webhook_max_age_s * 2)
    redis_ok = _claim_nonce_redis(nonce, ttl)
    if redis_ok is not None:
        return redis_ok
    return _claim_nonce_memory(nonce, ttl)


def parse_timestamp(raw: str | None) -> int | None:
    if raw is None:
        return None
    cleaned = raw.strip()
    if not cleaned or not cleaned.isdigit():
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def timestamp_fresh(ts: int, *, now: float | None = None, max_age_s: float | None = None) -> bool:
    age_limit = float(max_age_s if max_age_s is not None else settings.webhook_max_age_s)
    current = time.time() if now is None else now
    # Tolera skew curto no futuro (relogio do emissor adiantado).
    skew_future = min(60.0, age_limit)
    delta = current - float(ts)
    if delta < -skew_future:
        return False
    if delta > age_limit:
        return False
    return True


def verify_signature(
    *,
    secret: str,
    body: bytes,
    signature: str | None,
    timestamp: str | None,
    nonce: str | None,
    now: float | None = None,
    max_age_s: float | None = None,
    claim: bool = True,
) -> str | None:
    """Valida assinatura + janela + nonce.

    Retorna ``None`` se ok; senao mensagem de erro (401).
    Com ``claim=True`` (default) consome o nonce em caso de sucesso.
    """
    if not signature or not signature.strip():
        return "Assinatura ausente"
    if not timestamp or not str(timestamp).strip():
        return "Timestamp ausente"
    if not nonce or not str(nonce).strip():
        return "Nonce ausente"

    nonce_clean = str(nonce).strip()
    if len(nonce_clean) > 128:
        return "Nonce invalido"

    ts = parse_timestamp(str(timestamp))
    if ts is None:
        return "Timestamp invalido"

    if not timestamp_fresh(ts, now=now, max_age_s=max_age_s):
        return "Timestamp expirado"

    expected = sign(secret, str(ts), nonce_clean, body)
    if not hmac.compare_digest(expected, signature.strip()):
        return "Assinatura invalida"

    if claim and not claim_nonce(nonce_clean, ttl_s=(max_age_s or settings.webhook_max_age_s) * 2):
        return "Nonce reutilizado"

    return None
