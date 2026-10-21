"""STO-27: anti-replay no webhook de video (timestamp + nonce no HMAC)."""

from __future__ import annotations

import json
import time
import uuid

from app.config import settings
from app.database import get_db
from app.models import Job, JobStatus, JobType, Project, User
from app.services import webhook_auth


def _session(client):
    gen = client.app.dependency_overrides[get_db]()
    return next(gen)


def _seed_running_video_job(client) -> uuid.UUID:
    db = _session(client)
    try:
        user = User(email=f"wh-{uuid.uuid4().hex[:8]}@t.com", password_hash="x", credits=10)
        db.add(user)
        db.flush()
        project = Project(user_id=user.id, status="STORYBOARD_READY", child_name="Ana")
        db.add(project)
        db.flush()
        job = Job(
            project_id=project.id,
            type=JobType.VIDEO.value,
            status=JobStatus.RUNNING.value,
            provider="kling",
            cost_credits=1,
        )
        db.add(job)
        db.commit()
        return job.id
    finally:
        db.close()


def _signed_headers(body: bytes, *, ts: int | None = None, nonce: str | None = None) -> dict:
    timestamp = str(int(time.time()) if ts is None else ts)
    n = nonce or uuid.uuid4().hex
    sig = webhook_auth.sign(settings.webhook_signing_secret, timestamp, n, body)
    return {
        "X-Timestamp": timestamp,
        "X-Nonce": n,
        "X-Signature": sig,
        "Content-Type": "application/json",
    }


def test_sign_includes_timestamp_and_nonce():
    body = b'{"job_id":"x"}'
    a = webhook_auth.sign("secret", "1700000000", "nonce-a", body)
    b = webhook_auth.sign("secret", "1700000000", "nonce-b", body)
    c = webhook_auth.sign("secret", "1700000001", "nonce-a", body)
    assert a != b and a != c
    # Assinatura antiga so do body nao bate com o formato novo.
    import hashlib
    import hmac

    legacy = hmac.new(b"secret", body, hashlib.sha256).hexdigest()
    assert a != legacy


def test_verify_rejects_stale_timestamp():
    body = b"{}"
    ts = str(int(time.time()) - 10_000)
    nonce = "n1"
    sig = webhook_auth.sign(settings.webhook_signing_secret, ts, nonce, body)
    err = webhook_auth.verify_signature(
        secret=settings.webhook_signing_secret,
        body=body,
        signature=sig,
        timestamp=ts,
        nonce=nonce,
        max_age_s=300,
        claim=False,
    )
    assert err == "Timestamp expirado"


def test_verify_rejects_replayed_nonce():
    body = b"{}"
    ts = str(int(time.time()))
    nonce = f"replay-{uuid.uuid4().hex}"
    sig = webhook_auth.sign(settings.webhook_signing_secret, ts, nonce, body)
    kwargs = dict(
        secret=settings.webhook_signing_secret,
        body=body,
        signature=sig,
        timestamp=ts,
        nonce=nonce,
        max_age_s=300,
    )
    assert webhook_auth.verify_signature(**kwargs) is None
    assert webhook_auth.verify_signature(**kwargs) == "Nonce reutilizado"


def test_video_webhook_success(client, monkeypatch):
    monkeypatch.setattr(settings, "webhook_signing_secret", "test-webhook-secret")
    job_id = _seed_running_video_job(client)
    payload = {"job_id": str(job_id), "status": "success", "storage_key": "videos/ok.mp4"}
    raw = json.dumps(payload).encode()
    r = client.post("/v1/webhooks/video", content=raw, headers=_signed_headers(raw))
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True

    db = _session(client)
    try:
        job = db.get(Job, job_id)
        assert job is not None
        assert job.status == JobStatus.DONE.value
        assert job.result == {"video": "videos/ok.mp4"}
    finally:
        db.close()


def test_video_webhook_rejects_missing_anti_replay_headers(client, monkeypatch):
    monkeypatch.setattr(settings, "webhook_signing_secret", "test-webhook-secret")
    job_id = _seed_running_video_job(client)
    raw = json.dumps({"job_id": str(job_id), "status": "success", "storage_key": "v.mp4"}).encode()
    # Assinatura legada so do body — deve falhar (timestamp/nonce obrigatorios).
    import hashlib
    import hmac

    legacy = hmac.new(b"test-webhook-secret", raw, hashlib.sha256).hexdigest()
    r = client.post("/v1/webhooks/video", content=raw, headers={"X-Signature": legacy})
    assert r.status_code == 401
    assert "Timestamp" in r.json()["detail"] or "ausente" in r.json()["detail"]


def test_video_webhook_rejects_bad_signature(client, monkeypatch):
    monkeypatch.setattr(settings, "webhook_signing_secret", "test-webhook-secret")
    job_id = _seed_running_video_job(client)
    raw = json.dumps({"job_id": str(job_id), "status": "success", "storage_key": "v.mp4"}).encode()
    headers = _signed_headers(raw)
    headers["X-Signature"] = "0" * 64
    r = client.post("/v1/webhooks/video", content=raw, headers=headers)
    assert r.status_code == 401
    assert r.json()["detail"] == "Assinatura invalida"


def test_video_webhook_rejects_replay(client, monkeypatch):
    monkeypatch.setattr(settings, "webhook_signing_secret", "test-webhook-secret")
    job_id = _seed_running_video_job(client)
    raw = json.dumps({"job_id": str(job_id), "status": "success", "storage_key": "v.mp4"}).encode()
    headers = _signed_headers(raw, nonce="fixed-nonce-once")
    r1 = client.post("/v1/webhooks/video", content=raw, headers=headers)
    assert r1.status_code == 200, r1.text
    r2 = client.post("/v1/webhooks/video", content=raw, headers=headers)
    assert r2.status_code == 401
    assert r2.json()["detail"] == "Nonce reutilizado"


def test_video_webhook_rejects_stale(client, monkeypatch):
    monkeypatch.setattr(settings, "webhook_signing_secret", "test-webhook-secret")
    monkeypatch.setattr(settings, "webhook_max_age_s", 60.0)
    job_id = _seed_running_video_job(client)
    raw = json.dumps({"job_id": str(job_id), "status": "success", "storage_key": "v.mp4"}).encode()
    headers = _signed_headers(raw, ts=int(time.time()) - 600)
    r = client.post("/v1/webhooks/video", content=raw, headers=headers)
    assert r.status_code == 401
    assert r.json()["detail"] == "Timestamp expirado"
