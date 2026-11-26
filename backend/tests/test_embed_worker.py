"""O consumo de jobs na API acompanha seu ciclo de vida."""

import asyncio
import threading
import time

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.services import process_lifecycle


@pytest.fixture(autouse=True)
def isolated_shutdown_state(monkeypatch):
    monkeypatch.setattr(process_lifecycle, "_draining", threading.Event())


def test_lifespan_starts_and_stops_job_pump(monkeypatch):
    import app.main as mainmod

    monkeypatch.setattr(settings, "api_job_pump", True)
    events = []

    async def pump():
        events.append("started")
        try:
            while not process_lifecycle.draining():
                await asyncio.sleep(0.001)
        finally:
            events.append("stopped")

    monkeypatch.setattr("app.workers.api_pump.pump_forever", pump)
    with TestClient(mainmod.app) as client:
        assert client.get("/health").status_code == 200
        for _ in range(200):
            if events:
                break
            time.sleep(0.01)
        assert events == ["started"]
    assert events == ["started", "stopped"]


def test_job_pump_runs_outside_the_api_event_loop(monkeypatch):
    """Um job pesado (código síncrono) não pode travar o /health."""
    import app.main as mainmod

    monkeypatch.setattr(settings, "api_job_pump", True)
    busy = threading.Event()
    seen = {}

    async def pump():
        seen["thread"] = threading.current_thread().name
        busy.set()
        while not process_lifecycle.draining():
            time.sleep(0.05)  # simula montagem de PDF/imagem sem await

    monkeypatch.setattr("app.workers.api_pump.pump_forever", pump)
    with TestClient(mainmod.app) as client:
        assert busy.wait(2)
        started = time.monotonic()
        assert client.get("/health").status_code == 200
        assert time.monotonic() - started < 1.0
    assert seen["thread"] == "api-job-pump"


def test_lifespan_does_not_start_disabled_job_pump(monkeypatch):
    import app.main as mainmod

    monkeypatch.setattr(settings, "api_job_pump", False)
    events = []

    async def pump():
        events.append("started")

    monkeypatch.setattr("app.workers.api_pump.pump_forever", pump)
    with TestClient(mainmod.app) as client:
        assert client.get("/health").status_code == 200
    assert events == []
