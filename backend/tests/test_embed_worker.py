"""O consumo de jobs na API acompanha seu ciclo de vida."""

import asyncio
import threading

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
        assert events == ["started"]
    assert events == ["started", "stopped"]


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
