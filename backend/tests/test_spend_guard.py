"""STO-18: teto diario + falha antes do vendor."""

from datetime import UTC, datetime

import pytest

from app.config import settings
from app.database import get_db
from app.models import Job, JobStatus, JobType, Project, User
from app.services import spend_guard
from app.services.pricing import estimate_job_usd
from app.workers import handlers, runner


def _session(client):
    gen = client.app.dependency_overrides[get_db]()
    return next(gen)


def _add_photo(auth_client, pid):
    return auth_client.post(
        f"/v1/projects/{pid}/photos", json={"content_type": "image/jpeg", "ext": "jpg"}
    )


def _seed_measured(client, *, cost_usd: float, credits: int = 1, status=JobStatus.DONE.value):
    db = _session(client)
    try:
        user = db.query(User).first()
        if user is None:
            user = User(email="u@t.com", password_hash="x", credits=50)
            db.add(user)
            db.flush()
        project = Project(user_id=user.id, status="EBOOK_READY", child_name="Ana")
        db.add(project)
        db.flush()
        job = Job(
            project_id=project.id,
            type=JobType.EBOOK.value,
            status=status,
            provider="openai",
            cost_usd=cost_usd,
            cost_credits=credits,
            created_at=datetime.now(UTC),
        )
        db.add(job)
        db.commit()
        return job.id
    finally:
        db.close()


def test_estimate_ebook_uses_pages_and_refine(monkeypatch):
    monkeypatch.setattr(settings, "ebook_pages", 10)
    monkeypatch.setattr(settings, "price_openai_image_usd", 0.04)
    monkeypatch.setattr(settings, "ebook_face_match", True)
    monkeypatch.setattr(settings, "ebook_refine_scene", True)
    assert estimate_job_usd("EBOOK") == pytest.approx(0.8)


def test_enqueue_blocked_by_daily_usd_ceiling(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "daily_spend_usd_ceiling", 1.0)
    monkeypatch.setattr(settings, "daily_credits_ceiling", 0)
    monkeypatch.setattr(settings, "price_openai_image_usd", 0.10)
    _seed_measured(auth_client, cost_usd=0.95)

    r = auth_client.post("/v1/projects", json={"child_name": "Ana"})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    assert _add_photo(auth_client, pid).status_code == 201
    r = auth_client.post(f"/v1/projects/{pid}/avatar")
    assert r.status_code == 402, r.text
    assert "Teto diario de USD" in r.json()["detail"]


def test_enqueue_blocked_by_daily_credits_ceiling(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "credits_enabled", True)
    monkeypatch.setattr(settings, "daily_spend_usd_ceiling", 0.0)
    monkeypatch.setattr(settings, "daily_credits_ceiling", 1)
    _seed_measured(auth_client, cost_usd=0.01, credits=1)

    r = auth_client.post("/v1/projects", json={"child_name": "Ana"})
    pid = r.json()["id"]
    assert _add_photo(auth_client, pid).status_code == 201
    r = auth_client.post(f"/v1/projects/{pid}/avatar")
    assert r.status_code == 402, r.text
    assert "creditos" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_worker_blocks_vendor_when_usd_ceiling_hit(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "daily_spend_usd_ceiling", 0.5)
    monkeypatch.setattr(settings, "daily_credits_ceiling", 0)
    _seed_measured(auth_client, cost_usd=0.6)

    db = _session(auth_client)
    try:
        user = db.query(User).first()
        project = Project(user_id=user.id, status="CREATED", child_name="Ana")
        db.add(project)
        db.flush()
        job = Job(
            project_id=project.id,
            type=JobType.AVATAR.value,
            status=JobStatus.PENDING.value,
            cost_credits=1,
            created_at=datetime.now(UTC),
        )
        db.add(job)
        user.credits = max(user.credits - 1, 0)
        db.commit()
        db.refresh(job)
        job_id = job.id
        credits_before = user.credits
    finally:
        db.close()

    called = {"n": 0}

    async def boom(_db, _job):
        called["n"] += 1

    monkeypatch.setitem(handlers.HANDLERS, JobType.AVATAR.value, boom)

    db = _session(auth_client)
    try:
        job = db.get(Job, job_id)
        await runner.process_job(db, job)
        db.refresh(job)
        assert job.status == JobStatus.FAILED.value
        assert "Teto diario" in (job.error or "")
        assert called["n"] == 0
        user = db.query(User).first()
        assert user.credits == credits_before + 1  # estorno
    finally:
        db.close()


def test_usage_surfaces_anomalies(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "usage_dashboard_password", "segredo")
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    monkeypatch.setattr(settings, "daily_spend_usd_ceiling", 1.0)
    monkeypatch.setattr(settings, "spend_anomaly_warn_ratio", 0.5)
    _seed_measured(auth_client, cost_usd=0.8)

    r = auth_client.get("/v1/usage", headers={"X-Usage-Password": "segredo"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["daily_spend_usd_ceiling"] == 1.0
    assert body["today_credits"] >= 1
    kinds = {a["kind"] for a in body["anomalies"]}
    assert "daily_usd_warn" in kinds or "daily_usd_ceiling" in kinds


def test_ceilings_disabled_by_default(auth_client):
    db = _session(auth_client)
    try:
        spend = spend_guard.day_spend(db)
        assert spend.committed_usd == 0.0
    finally:
        db.close()
    r = auth_client.post("/v1/projects", json={"child_name": "Ana"})
    pid = r.json()["id"]
    assert _add_photo(auth_client, pid).status_code == 201
    r = auth_client.post(f"/v1/projects/{pid}/avatar")
    assert r.status_code == 202, r.text
