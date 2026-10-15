"""Corrida de Idempotency-Key no enqueue não pode virar HTTP 500."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
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
