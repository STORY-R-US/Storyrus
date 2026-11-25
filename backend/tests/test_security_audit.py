"""Correções da auditoria de segurança de 25/11/2026."""

import base64
import hashlib
import hmac
import time
import uuid

import pytest
from fastapi import HTTPException

from app import storage
from app.config import Settings, settings
from app.database import get_db
from app.models import Job, JobStatus, Project, User
from app.services import jobs as jobs_svc


def _session(client):
    gen = client.app.dependency_overrides[get_db]()
    return next(gen)


def _password_mode(monkeypatch, *, max_attempts=3, global_max=20):
    monkeypatch.setattr(settings, "usage_dashboard_password", "senha-certa")
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    monkeypatch.setattr(settings, "owner_emails", "")
    monkeypatch.setattr(settings, "owner_password_fallback", True)
    monkeypatch.setattr(settings, "usage_lockout_max_attempts", max_attempts)
    monkeypatch.setattr(settings, "usage_lockout_global_max_attempts", global_max)


def test_shared_password_is_off_by_default():
    assert Settings.model_fields["owner_password_fallback"].default is False


def test_shared_password_rejected_when_fallback_off(client, monkeypatch):
    _password_mode(monkeypatch)
    monkeypatch.setattr(settings, "owner_password_fallback", False)
    r = client.get("/v1/users", headers={"X-Usage-Password": "senha-certa"})
    assert r.status_code == 401


def test_correct_password_does_not_pass_during_lockout(client, monkeypatch):
    _password_mode(monkeypatch, max_attempts=3)
    for _ in range(3):
        client.get("/v1/users", headers={"X-Usage-Password": "errada"})
    r = client.get("/v1/users", headers={"X-Usage-Password": "senha-certa"})
    assert r.status_code == 429


def test_rotating_forwarded_for_hits_global_lockout(client, monkeypatch):
    _password_mode(monkeypatch, max_attempts=3, global_max=5)
    for n in range(5):
        client.get(
            "/v1/users",
            headers={"X-Usage-Password": "errada", "X-Forwarded-For": f"10.0.0.{n}"},
        )
    r = client.get(
        "/v1/users",
        headers={"X-Usage-Password": "senha-certa", "X-Forwarded-For": "10.9.9.9"},
    )
    assert r.status_code == 429


def _user_with_jobs(client, count: int) -> tuple[uuid.UUID, uuid.UUID]:
    db = _session(client)
    try:
        user = User(
            email=f"limite-{uuid.uuid4().hex[:8]}@example.com",
            password_hash="!clerk",
            credits=0,
        )
        db.add(user)
        db.flush()
        project = Project(user_id=user.id, style="cgi_3d")
        db.add(project)
        db.flush()
        for _ in range(count):
            db.add(Job(project_id=project.id, type="AVATAR", status=JobStatus.DONE.value))
        db.commit()
        return user.id, project.id
    finally:
        db.close()


def test_daily_job_cap_blocks_extra_generation(client, monkeypatch):
    monkeypatch.setattr(settings, "max_jobs_per_user_per_day", 3)
    user_id, _ = _user_with_jobs(client, 3)
    db = _session(client)
    try:
        user = db.get(User, user_id)
        with pytest.raises(HTTPException) as exc:
            jobs_svc._check_daily_user_jobs(db, user)
        assert exc.value.status_code == 429
    finally:
        db.close()


def test_daily_job_cap_allows_under_limit_and_can_be_disabled(client, monkeypatch):
    monkeypatch.setattr(settings, "max_jobs_per_user_per_day", 3)
    user_id, _ = _user_with_jobs(client, 2)
    db = _session(client)
    try:
        user = db.get(User, user_id)
        jobs_svc._check_daily_user_jobs(db, user)
        monkeypatch.setattr(settings, "max_jobs_per_user_per_day", 0)
        jobs_svc._check_daily_user_jobs(db, user)
    finally:
        db.close()


def test_admin_delete_user_removes_stored_files(auth_client, monkeypatch):
    _password_mode(monkeypatch, max_attempts=10)
    headers = {"X-Usage-Password": "senha-certa"}
    created = auth_client.post("/v1/projects", json={"style": "cgi_3d"})
    assert created.status_code == 201, created.text
    project_id = created.json()["id"]

    purged: list[str] = []
    monkeypatch.setattr(storage, "delete_project_objects", lambda pid: purged.append(str(pid)))
    monkeypatch.setattr(storage, "delete_key", lambda key: None)

    listed = auth_client.get("/v1/users", headers=headers).json()
    me = next(u for u in listed["users"] if u["email"] == "auth@example.com")
    r = auth_client.delete(f"/v1/users/{me['id']}", headers=headers)
    assert r.status_code == 204, r.text
    assert purged == [project_id]
    db = _session(auth_client)
    try:
        assert db.query(Project).count() == 0
        assert db.query(User).filter(User.email == "auth@example.com").first() is None
    finally:
        db.close()


def _sign_svix(secret: str, body: bytes, svix_id: str, timestamp: str) -> str:
    raw = secret.removeprefix("whsec_")
    key = base64.b64decode(raw + "=" * (-len(raw) % 4))
    signed = f"{svix_id}.{timestamp}.".encode() + body
    return "v1," + base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()


def test_clerk_webhook_replay_is_ignored(client, monkeypatch):
    secret = "whsec_" + base64.b64encode(b"replay-secret").decode()
    monkeypatch.setattr(settings, "clerk_webhook_secret", secret)
    calls: list[str] = []
    monkeypatch.setattr(
        "app.routers.webhooks.apply_clerk_event",
        lambda db, kind, data: calls.append(kind),
    )
    body = b'{"type":"user.updated","data":{"id":"user_x"}}'
    svix_id = "msg_" + uuid.uuid4().hex
    ts = str(int(time.time()))
    headers = {
        "svix-id": svix_id,
        "svix-timestamp": ts,
        "svix-signature": _sign_svix(secret, body, svix_id, ts),
        "content-type": "application/json",
    }
    first = client.post("/v1/webhooks/clerk", content=body, headers=headers)
    again = client.post("/v1/webhooks/clerk", content=body, headers=headers)
    assert first.status_code == 200 and again.status_code == 200
    assert again.json().get("duplicate") is True
    assert calls == ["user.updated"]
