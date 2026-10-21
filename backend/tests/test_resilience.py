"""Testes da espera paciente (retry_until) e da classificacao de queda."""

from __future__ import annotations

import httpx
import pytest

from app.ai_clients import resilience
from app.ai_clients.base import ProviderError
from app.ai_clients.resilience import OutageError, is_outage, retry_until


@pytest.fixture(autouse=True)
def slept(monkeypatch):
    """Relogio falso: cada espera "passa" o tempo, sem test lento."""
    now = {"t": 0.0}
    waits: list[float] = []

    async def fake_sleep(delay: float) -> None:
        waits.append(delay)
        now["t"] += delay

    monkeypatch.setattr(resilience.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(resilience.time, "monotonic", lambda: now["t"])
    monkeypatch.setattr(resilience.random, "uniform", lambda _a, b: b)
    return waits


def test_is_outage_follows_provider_classification():
    assert is_outage(ProviderError("Gemini 503", transient=True, status_code=503))
    assert is_outage(OutageError("fora", status_code=500))
    assert is_outage(httpx.ConnectError(""))
    assert not is_outage(ProviderError("creditos esgotados", transient=False, status_code=429))
    assert not is_outage(ProviderError("Gemini 400", transient=False, status_code=400))
    assert not is_outage(ValueError("prompt invalido"))


@pytest.mark.asyncio
async def test_retries_transient_until_success(slept):
    calls = {"n": 0}

    async def fn():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ProviderError("Gemini 503", transient=True, status_code=503)
        return "ok"

    assert await retry_until("pagina", fn, budget_s=600, log=lambda _m: None) == "ok"
    assert calls["n"] == 3
    assert len(slept) == 2


@pytest.mark.asyncio
async def test_permanent_error_aborts_on_first_failure(slept):
    calls = {"n": 0}

    async def fn():
        calls["n"] += 1
        raise ProviderError("creditos esgotados", transient=False, status_code=429)

    with pytest.raises(ProviderError) as ei:
        await retry_until("avatar", fn, budget_s=600, log=lambda _m: None)

    assert not isinstance(ei.value, OutageError)
    assert calls["n"] == 1
    assert slept == []


@pytest.mark.asyncio
async def test_outage_error_when_budget_runs_out():
    async def fn():
        raise ProviderError("Gemini 503", transient=True, status_code=503)

    with pytest.raises(OutageError) as ei:
        await retry_until("pagina 03", fn, budget_s=0, log=lambda _m: None)

    assert ei.value.status_code == 503
    assert ei.value.attempts == 1
    assert ei.value.transient is True
    assert "pagina 03" in str(ei.value)
    assert "retome com o mesmo comando" in str(ei.value)


@pytest.mark.asyncio
async def test_budget_caps_total_waiting(slept):
    async def fn():
        raise ProviderError("Gemini 500", transient=True, status_code=500)

    with pytest.raises(OutageError) as ei:
        await retry_until(
            "pagina", fn, budget_s=10, base_s=2.0, max_wait_s=8.0, log=lambda _m: None
        )

    # Esperas de 2s e 4s cabem nos 10s; a de 8s nao, e o run desiste ali.
    assert slept == [2.0, 4.0]
    assert ei.value.attempts == 3


def test_backoff_delay_respects_cap():
    assert resilience.backoff_delay(1, base_s=2.0, max_s=60.0) == 2.0
    assert resilience.backoff_delay(4, base_s=2.0, max_s=60.0) == 16.0
    assert resilience.backoff_delay(10, base_s=2.0, max_s=60.0) == 60.0
