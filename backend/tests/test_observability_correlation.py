"""STO-29: request ID, logs JSON, correlacao job ↔ Opik metadata."""

from __future__ import annotations

import json
import logging
from io import StringIO
from types import SimpleNamespace

import pytest

from app.observability.context import correlation_scope, get_request_id
from app.observability.logging_setup import CorrelationFilter, JsonFormatter, configure_logging
from app.observability.opik_trace import job_metadata


def test_health_echoes_generated_request_id(client):
    r = client.get("/health")
    assert r.status_code == 200
    rid = r.headers.get("X-Request-ID")
    assert rid
    assert len(rid) >= 8


def test_health_echoes_client_request_id(client):
    r = client.get("/health", headers={"X-Request-ID": "client-corr-abc"})
    assert r.status_code == 200
    assert r.headers.get("X-Request-ID") == "client-corr-abc"


def test_enqueue_persists_request_id(auth_client):
    rid = "corr-enqueue-42"
    p = auth_client.post("/v1/projects", json={"style": "cgi_3d", "child_name": "Ana"})
    assert p.status_code == 201, p.text
    project_id = p.json()["id"]

    # Foto obrigatoria para avatar? Avatar exige fotos no worker, mas enqueue aceita.
    # story nao precisa de foto.
    r = auth_client.post(
        f"/v1/projects/{project_id}/story",
        headers={"X-Request-ID": rid, "Idempotency-Key": "sto29-story-1"},
    )
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["request_id"] == rid
    assert r.headers.get("X-Request-ID") == rid

    job = auth_client.get(f"/v1/jobs/{body['job_id']}")
    assert job.status_code == 200, job.text
    assert job.json()["request_id"] == rid


def test_json_formatter_includes_correlation_fields():
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(CorrelationFilter())
    handler.setFormatter(JsonFormatter())
    log = logging.getLogger("test.sto29.json")
    log.handlers.clear()
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False

    with correlation_scope(request_id="rid-1", job_id="jid-1", service="worker"):
        log.info("hello %s", "world")

    line = stream.getvalue().strip()
    payload = json.loads(line)
    assert payload["msg"] == "hello world"
    assert payload["request_id"] == "rid-1"
    assert payload["job_id"] == "jid-1"
    assert payload["service"] == "worker"
    assert payload["level"] == "INFO"


def test_job_metadata_includes_request_id():
    job = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001",
        type="STORY",
        project_id="00000000-0000-0000-0000-000000000002",
        attempts=1,
        request_id="from-api",
    )
    meta = job_metadata(job)
    assert meta["request_id"] == "from-api"
    assert meta["job_id"] == "00000000-0000-0000-0000-000000000001"
    assert meta["job_type"] == "STORY"


def test_configure_logging_json_and_resolved_format():
    from app.config import Settings

    s = Settings(
        app_env="prod",
        log_format="auto",
        jwt_secret="prod-secret-ok",
        webhook_signing_secret="prod-wh-ok",
        openai_api_key="sk-openai-test-key",
    )
    assert s.resolved_log_format() == "json"
    s_dev = Settings(app_env="dev", log_format="auto")
    assert s_dev.resolved_log_format() == "text"

    configure_logging(level="INFO", fmt="json", service="api")
    assert get_request_id() is None  # service set, request unset


@pytest.mark.asyncio
async def test_worker_process_binds_request_id(monkeypatch):
    """process_job liga request_id do job no contexto de log."""
    from app.models import Job, JobStatus, JobType
    from app.services import spend_guard
    from app.workers import runner

    seen: dict[str, str | None] = {}

    async def fake_handler(db, job):
        seen["request_id"] = get_request_id()

    monkeypatch.setitem(
        __import__("app.workers.handlers", fromlist=["HANDLERS"]).HANDLERS,
        "STORY",
        fake_handler,
    )
    monkeypatch.setattr(runner.settings, "job_heartbeat_interval_s", 0)
    monkeypatch.setattr(
        spend_guard,
        "assert_vendor_allowed",
        lambda db, job_type=None: None,
    )

    class _DB:
        def commit(self):
            return None

    job = Job(
        project_id=__import__("uuid").uuid4(),
        type=JobType.STORY.value,
        status=JobStatus.PENDING.value,
        request_id="worker-rid",
        cost_credits=0,
    )
    job.id = __import__("uuid").uuid4()
    job.attempts = 0

    await runner.process_job(_DB(), job)
    assert seen["request_id"] == "worker-rid"
    assert job.status == JobStatus.DONE.value
