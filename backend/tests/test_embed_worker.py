"""O consumo de jobs na API acompanha seu ciclo de vida."""

import asyncio

from fastapi.testclient import TestClient

from app.config import settings


def test_lifespan_starts_and_stops_job_pump(monkeypatch):
    import app.main as mainmod

    monkeypatch.setattr(settings, "api_job_pump", True)
    events = []

    async def pump():
        events.append("started")
        try:
            await asyncio.Future()
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
