"""Conta OpenAI sem credito. Rate limit (429 de cota momentanea) nao entra aqui."""

from __future__ import annotations

_CREDIT_MARKERS = (
    "insufficient_quota",
    "billing_hard_limit",
    "exceeded your current quota",
    "check your plan and billing",
    "billing_not_active",
)


def openai_credits_exhausted(status_code: int | None, body: str | None) -> bool:
    """True quando a resposta da OpenAI e saldo/plano esgotado, nao fila cheia."""
    if status_code == 402:
        return True
    lower = (body or "").lower()
    return any(marker in lower for marker in _CREDIT_MARKERS)
