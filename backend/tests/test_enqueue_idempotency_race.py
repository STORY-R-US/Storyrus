"""Corrida de Idempotency-Key no enqueue não pode virar HTTP 500."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Job, JobStatus, JobType, Project, User
from app.services import jobs as jobs_svc


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.mark.parametrize("mismatch", ["project", "step"])
def test_idempotency_key_cannot_resume_another_book_or_step(session_factory, mismatch):
    with session_factory() as db:
        user = User(email="scope@test.app", password_hash="x", credits=10)
        db.add(user)
        db.flush()
        project = Project(user_id=user.id, style="cartoon")
        other = Project(user_id=user.id, style="cartoon")
        db.add_all([project, other])
        db.flush()
        original = Job(
            project_id=project.id, type="AVATAR", status="PENDING", idempotency_key="same-key"
        )
        db.add(original)
        db.commit()
        with pytest.raises(HTTPException) as caught:
            jobs_svc.enqueue_job(
                db,
                user=user,
                project=other if mismatch == "project" else project,
                job_type=JobType.EBOOK if mismatch == "step" else JobType.AVATAR,
                idempotency_key="same-key",
            )
        assert caught.value.status_code == 409
        db.refresh(user)
        assert user.credits == 10 and db.query(Job).count() == 1


@pytest.mark.parametrize("terminal_status", ["FAILED", "DONE"])
def test_duplicate_failure_cannot_refund_twice_or_replace_completed_job(
    session_factory, terminal_status
):
    with session_factory() as db:
        user = User(email="refund@test.app", password_hash="x", credits=8)
        db.add(user)
        db.flush()
        project = Project(user_id=user.id, style="cartoon")
        db.add(project)
        db.flush()
        job = Job(project_id=project.id, type="EBOOK", status="RUNNING", cost_credits=2)
        db.add(job)
        db.commit()
        if terminal_status == "FAILED":
            job.result = {"last_provider_error": {"outcome_unknown": True}}
            jobs_svc.mark_failed_and_refund(db, job, "first failure")
            assert job.result["last_provider_error"]["outcome_unknown"] is True
        else:
            job.status = "DONE"
            db.commit()
        # A stale object from a second worker still thinks the task is running.
        job.status = "RUNNING"
        jobs_svc.mark_failed_and_refund(db, job, "late duplicate failure")
        db.refresh(user)
        db.refresh(job)
        assert job.status == terminal_status
        assert user.credits == (10 if terminal_status == "FAILED" else 8)
        assert job.error == ("first failure" if terminal_status == "FAILED" else None)


@pytest.mark.parametrize("operation,expected", [("debit", 6), ("refund", 14)])
def test_credit_updates_reload_balance_after_another_worker(session_factory, operation, expected):
    from app.services import credits

    with session_factory() as first, session_factory() as second:
        user = User(email="balance@test.app", password_hash="x", credits=10)
        first.add(user)
        first.commit()
        stale = second.get(User, user.id)
        assert stale.credits == 10
        change = getattr(credits, operation)
        change(first, user.id, 2)
        first.commit()
        change(second, user.id, 2)
        second.commit()
        first.refresh(user)
        assert user.credits == expected


def test_enqueue_job_returns_existing_on_idempotency_integrity_error(session_factory):
    db = session_factory()
    user = User(
        email=f"race-{uuid.uuid4().hex}@test.app",
        password_hash="x",
        credits=10,
        email_verified_at=datetime.now(UTC),
    )
    db.add(user)
    db.flush()
    project = Project(user_id=user.id, status="CREATED", style="cartoon")
    db.add(project)
    db.commit()
    db.refresh(user)
    db.refresh(project)

    key = f"race-key-{uuid.uuid4().hex}"
    real_commit = db.commit

    def commit_with_race():
        # Outra transação “ganhou” a mesma Idempotency-Key.
        side = session_factory()
        side.add(
            Job(
                project_id=project.id,
                type=JobType.AVATAR.value,
                status=JobStatus.PENDING.value,
                idempotency_key=key,
                cost_credits=1,
                result={"payload": {"preview_chain": True}},
            )
        )
        side.commit()
        side.close()
        try:
            return real_commit()
        except IntegrityError:
            raise

    db.commit = commit_with_race  # type: ignore[method-assign]

    job = jobs_svc.enqueue_job(
        db,
        user=user,
        project=project,
        job_type=JobType.AVATAR,
        idempotency_key=key,
        payload={"preview_chain": True},
    )
    assert job.idempotency_key == key
    assert job.type == JobType.AVATAR.value
    db.close()


def test_enqueue_job_returns_row_when_refresh_fails(session_factory):
    """Commit ok + refresh quebrado devolve o job. Não propaga 500."""
    db = session_factory()
    user = User(
        email=f"refresh-{uuid.uuid4().hex}@test.app",
        password_hash="x",
        credits=10,
        email_verified_at=datetime.now(UTC),
    )
    db.add(user)
    db.flush()
    project = Project(user_id=user.id, status="CREATED", style="cartoon")
    db.add(project)
    db.commit()
    db.refresh(user)
    db.refresh(project)

    key = f"refresh-key-{uuid.uuid4().hex}"
    real_refresh = db.refresh

    def refresh_boom(obj, *args, **kwargs):
        if isinstance(obj, Job):
            raise RuntimeError("refresh")
        return real_refresh(obj, *args, **kwargs)

    db.refresh = refresh_boom  # type: ignore[method-assign]

    job = jobs_svc.enqueue_job(
        db,
        user=user,
        project=project,
        job_type=JobType.AVATAR,
        idempotency_key=key,
        payload={"preview_chain": True, "brief": "oi\x00"},
    )
    assert job.idempotency_key == key
    assert job.type == JobType.AVATAR.value
    assert "\x00" not in (job.result or {}).get("payload", {}).get("brief", "")
    db.close()
