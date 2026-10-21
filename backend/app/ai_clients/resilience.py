"""Espera paciente para quedas do provedor de imagem.

Queda (500/502/503/504, 429 de cota, rede) e diferente de erro nosso (400,
credito esgotado, chave ausente): a primeira pede espera, a segunda pede
aborto imediato. `retry_until` insiste dentro de um orcamento de tempo e
termina com `OutageError` em vez de girar para sempre.
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

from app.ai_clients.base import ProviderError

T = TypeVar("T")

OUTAGE_STATUS = frozenset({429, 500, 502, 503, 504})


class OutageError(ProviderError):
    """Provedor de imagem indisponivel apos esgotar a paciencia."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        attempts: int = 0,
        elapsed_s: float = 0.0,
    ):
        super().__init__(message, transient=True, status_code=status_code)
        self.attempts = attempts
        self.elapsed_s = elapsed_s


def is_outage(exc: BaseException) -> bool:
    """True quando vale esperar: indisponibilidade do provedor, nao erro de pedido.

    Em `ProviderError` quem classifica e o proprio provedor: 429 de cota vem
    `transient=True`, 429 de credito esgotado vem `transient=False`.
    """
    if isinstance(exc, OutageError):
        return True
    if isinstance(exc, ProviderError):
        return exc.transient
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in OUTAGE_STATUS
    if isinstance(exc, httpx.RequestError):
        return True
    return False


def backoff_delay(attempt: int, *, base_s: float = 2.0, max_s: float = 180.0) -> float:
    """Backoff exponencial com full jitter: uniform(0, min(max, base * 2^(attempt-1)))."""
    raw = min(max_s, base_s * (2 ** max(0, attempt - 1)))
    return random.uniform(0, raw) if raw > 0 else 0.0


def _describe(exc: BaseException) -> str:
    status = getattr(exc, "status_code", None)
    detail = str(exc).strip() or type(exc).__name__
    return f"{status} - {detail}" if status else detail


async def retry_until(
    label: str,
    fn: Callable[[], Awaitable[T]],
    *,
    budget_s: float,
    base_s: float = 2.0,
    max_wait_s: float = 180.0,
    log: Callable[[str], None] = print,
) -> T:
    """Repete `fn` enquanto o provedor estiver fora e houver orcamento.

    Erro nao-transitorio sobe na hora. Orcamento estourado levanta `OutageError`
    com o resumo da tentativa, para o chamador salvar o progresso e sair.
    """
    started = time.monotonic()
    attempt = 0
    while True:
        attempt += 1
        try:
            return await fn()
        except Exception as exc:  # noqa: BLE001 - reclassificado abaixo
            if not is_outage(exc):
                raise
            elapsed = time.monotonic() - started
            delay = backoff_delay(attempt, base_s=base_s, max_s=max_wait_s)
            if elapsed + delay >= budget_s:
                raise OutageError(
                    f"gerador de imagens fora em '{label}': {_describe(exc)} "
                    f"({attempt} tentativas / {elapsed / 60:.0f}min); "
                    "retome com o mesmo comando",
                    status_code=getattr(exc, "status_code", None),
                    attempts=attempt,
                    elapsed_s=elapsed,
                ) from exc
            left = (budget_s - elapsed) / 60
            log(
                f"{label}: {_describe(exc)} - tentativa {attempt}, "
                f"espera {delay:.0f}s, orcamento restante {left:.0f}min"
            )
            await asyncio.sleep(delay)
