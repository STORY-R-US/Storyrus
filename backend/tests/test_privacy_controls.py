"""Authorization, private delivery and complete deletion for adult accounts."""

import time
import uuid
from io import BytesIO
from urllib.parse import urlsplit

import pytest
from PIL import Image

from app import storage
from app.config import settings
from app.models import Asset, Project, UserVoice
from tests.conftest import _db

AUTHORIZATION = {"guardian_consent": True, "consent_version": "2026-10-29"}


def _image():
    data = BytesIO()
    image = Image.new("RGB", (40, 60), "blue")
    image.save(data, format="JPEG", exif=Image.Exif())
    return data.getvalue()


@pytest.mark.parametrize("path", ["photos", "photo", "extra-character"])
def test_no_media_is_accepted_without_explicit_current_authorization(
    auth_client, monkeypatch, path
):
    pid = auth_client.post("/v1/projects", json={}).json()["id"]
    put = []
    monkeypatch.setattr(storage, "put_bytes", lambda *args: put.append(args))
    if path == "photos":
        response = auth_client.post(f"/v1/projects/{pid}/{path}", json={})
    else:
        response = auth_client.post(
            f"/v1/projects/{pid}/{path}", files={"file": ("a.jpg", _image(), "image/jpeg")}
        )
    assert response.status_code == 403
    assert put == []


def test_authorization_is_recorded_with_the_photo(auth_client, monkeypatch):
    monkeypatch.setattr(storage, "put_bytes", lambda *args: None)
    pid = auth_client.post("/v1/projects", json={}).json()["id"]
    response = auth_client.post(
        f"/v1/projects/{pid}/photo",
        data=AUTHORIZATION,
        files={"file": ("a.jpg", _image(), "image/jpeg")},
    )
    assert response.status_code == 201, response.text
    db = _db(auth_client)
    try:
        asset = db.get(Asset, uuid.UUID(response.json()["asset_id"]))
        record = asset.meta["adult_authorization"]
        assert record["notice_version"] == "2026-10-29"
        assert record["adult_user_id"] == str(asset.project.user_id)
        assert record["scope"] == "book_photos"
        assert record["accepted_at"]
        assert record["method"] != "verifiable_parental_consent"
    finally:
        db.close()


def test_old_notice_is_not_accepted(auth_client):
    pid = auth_client.post("/v1/projects", json={}).json()["id"]
    response = auth_client.post(
        f"/v1/projects/{pid}/photos", json={"guardian_consent": True, "consent_version": "old"}
    )
    assert response.status_code == 403


def test_voice_needs_separate_adult_authorization(auth_client):
    response = auth_client.post(
        "/v1/voices", data={"name": "Minha voz"}, files={"file": ("a.mp3", b"audio", "audio/mpeg")}
    )
    assert response.status_code == 403


def test_local_storage_requires_expiring_method_bound_signature(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "storage_local_dir", str(tmp_path))
    monkeypatch.setattr(storage, "_internal_client", lambda: None)
    monkeypatch.setattr(storage, "_public_client", lambda: None)
    key = f"projects/{uuid.uuid4()}/photo/child.jpg"
    storage.put_bytes(key, b"private")
    assert client.get(f"/v1/local-storage/{key}").status_code == 403
    signed = storage.presign_get(key)
    response = client.get(signed)
    assert response.status_code == 200 and response.content == b"private"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert client.put(signed, content=b"overwrite").status_code == 403
    assert client.get(signed.replace("child.jpg", "another.jpg")).status_code == 403
    monkeypatch.setattr(time, "time", lambda: 10**12)
    assert client.get(signed).status_code == 403


def test_signed_put_does_not_authorize_download(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "storage_local_dir", str(tmp_path))
    monkeypatch.setattr(storage, "_internal_client", lambda: None)
    monkeypatch.setattr(storage, "_public_client", lambda: None)
    key = f"projects/{uuid.uuid4()}/photo/child.jpg"
    signed = storage.presign_put(key, "image/jpeg")
    assert client.put(signed, content=b"private").status_code == 204
    assert client.get(signed).status_code == 403
    assert urlsplit(signed).query


def test_deleting_project_removes_watermarks_and_superseded_objects(
    auth_client, monkeypatch, tmp_path
):
    monkeypatch.setattr(settings, "storage_local_dir", str(tmp_path))
    monkeypatch.setattr(storage, "_internal_client", lambda: None)
    pid = auth_client.post("/v1/projects", json={}).json()["id"]
    db = _db(auth_client)
    try:
        original = f"projects/{pid}/photo/original.jpg"
        marked = f"projects/{pid}/preview-mark/marked.png"
        orphan = f"projects/{pid}/cover/previous-version.png"
        for key in [original, marked, orphan]:
            storage.put_bytes(key, b"private")
        db.add(
            Asset(
                project_id=uuid.UUID(pid),
                kind="photo",
                storage_key=original,
                meta={"watermark_key": marked},
            )
        )
        db.commit()
    finally:
        db.close()
    assert auth_client.delete(f"/v1/projects/{pid}").status_code == 204
    for key in [original, marked, orphan]:
        assert not (tmp_path / key).exists()


def test_failed_storage_cleanup_does_not_claim_success(auth_client, monkeypatch):
    pid = auth_client.post("/v1/projects", json={}).json()["id"]

    def fail(*args):
        raise RuntimeError("storage unavailable")

    monkeypatch.setattr(storage, "delete_project_objects", fail)
    assert auth_client.delete(f"/v1/projects/{pid}").status_code == 503
    assert auth_client.get(f"/v1/projects/{pid}").status_code == 200


def test_removing_voice_also_removes_the_original_sample(auth_client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "storage_local_dir", str(tmp_path))
    monkeypatch.setattr(storage, "_internal_client", lambda: None)
    db = _db(auth_client)
    try:
        user_id = uuid.UUID(auth_client.get("/v1/auth/me").json()["id"])
        key = f"users/{user_id}/voices/private.mp3"
        storage.put_bytes(key, b"voice")
        voice = UserVoice(
            user_id=user_id,
            name="Adulto",
            elevenlabs_voice_id="voice-test",
            sample_storage_key=key,
            mime_type="audio/mpeg",
        )
        db.add(voice)
        db.commit()
        voice_id = str(voice.id)
    finally:
        db.close()

    async def delete_remote(_voice_id):
        return None

    monkeypatch.setattr("app.routers.voices.delete_cloned_voice", delete_remote)
    assert auth_client.delete(f"/v1/voices/{voice_id}").status_code == 204
    assert not (tmp_path / key).exists()


def test_uploaded_photo_drops_exif_and_keeps_correct_orientation():
    from app.routers.projects.photos import _normalize_photo

    raw = BytesIO()
    image = Image.new("RGB", (40, 60), "blue")
    exif = Image.Exif()
    exif[274] = 6
    exif[270] = "private location metadata"
    image.save(raw, format="JPEG", exif=exif)
    normalized = Image.open(BytesIO(_normalize_photo(raw.getvalue())))
    assert normalized.size == (60, 40)
    assert not normalized.getexif()


def test_production_uploads_cannot_bypass_metadata_removal(auth_client, monkeypatch):
    from app.deps import get_current_user
    from app.models import User

    pid = auth_client.post("/v1/projects", json={}).json()["id"]
    user_id = uuid.UUID(auth_client.get("/v1/auth/me").json()["id"])
    db = _db(auth_client)
    user = db.get(User, user_id)
    auth_client.app.dependency_overrides[get_current_user] = lambda: user
    monkeypatch.setattr(settings, "app_env", "prod")
    try:
        assert auth_client.post(f"/v1/projects/{pid}/photos", json=AUTHORIZATION).status_code == 410
    finally:
        auth_client.app.dependency_overrides.pop(get_current_user)
        db.close()


def test_retention_excludes_recent_active_and_paid_projects(auth_client):
    from datetime import UTC, datetime, timedelta

    from app.models import Job, PrintOrder
    from app.services.privacy_retention import retention_candidates

    ids = [auth_client.post("/v1/projects", json={}).json()["id"] for _ in range(4)]
    db = _db(auth_client)
    try:
        old = datetime.now(UTC) - timedelta(days=120)
        for pid in ids:
            db.get(Project, uuid.UUID(pid)).created_at = old
            db.get(Project, uuid.UUID(pid)).last_accessed_at = old
        db.get(Project, uuid.UUID(ids[1])).created_at = datetime.now(UTC)
        db.add(Job(project_id=uuid.UUID(ids[2]), type="EBOOK", status="RUNNING", cost_credits=0))
        db.add(PrintOrder(project_id=uuid.UUID(ids[3]), code="PRIVACY-PAID", payment_status="paid"))
        db.commit()
        assert [str(project.id) for project in retention_candidates(db, days=90)] == [ids[0]]
    finally:
        db.close()


def test_external_tracing_is_off_even_if_credentials_are_present(monkeypatch):
    from app.observability.opik_trace import enabled

    monkeypatch.setattr(settings, "privacy_allow_external_tracing", False)
    monkeypatch.setattr(settings, "opik_api_key", "configured-but-not-authorized")
    assert enabled() is False


def test_existing_media_requires_a_new_record_before_more_generation(auth_client):
    from fastapi import HTTPException

    from app.models import JobType
    from app.services import jobs

    pid = auth_client.post("/v1/projects", json={}).json()["id"]
    db = _db(auth_client)
    try:
        project = db.get(Project, uuid.UUID(pid))
        db.add(Asset(project_id=project.id, kind="photo", storage_key="old-photo.jpg"))
        db.commit()
        with pytest.raises(HTTPException) as rejected:
            jobs.enqueue_job(db, user=project.user, project=project, job_type=JobType.AVATAR)
        assert rejected.value.status_code == 403
        assert auth_client.get(f"/v1/projects/{pid}").status_code == 200
        response = auth_client.post(f"/v1/projects/{pid}/privacy/authorize", json=AUTHORIZATION)
        assert response.status_code == 204
        db.expire_all()
        from app.services.privacy import photos_authorized

        assert photos_authorized(db, uuid.UUID(pid))
    finally:
        db.close()


def test_parent_cannot_authorize_another_accounts_photos(auth_client, client):
    from tests.conftest import signup_and_verify

    pid = auth_client.post("/v1/projects", json={}).json()["id"]
    other = signup_and_verify(client, "other-parent@example.test")
    response = client.post(
        f"/v1/projects/{pid}/privacy/authorize",
        json=AUTHORIZATION,
        headers={"Authorization": f"Bearer {other}"},
    )
    assert response.status_code == 404


def test_active_generation_cannot_recreate_files_during_deletion(auth_client):
    from app.models import Job

    pid = auth_client.post("/v1/projects", json={}).json()["id"]
    db = _db(auth_client)
    try:
        db.add(Job(project_id=uuid.UUID(pid), type="EBOOK", status="RUNNING", cost_credits=0))
        db.commit()
    finally:
        db.close()
    assert auth_client.delete(f"/v1/projects/{pid}").status_code == 409
    assert auth_client.get(f"/v1/projects/{pid}").status_code == 200


def test_voice_authorization_migration_preserves_existing_records():
    import importlib.util
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import create_engine, inspect, text

    file = Path(__file__).parents[1] / "alembic/versions/0030_voice_authorization.py"
    spec = importlib.util.spec_from_file_location("voice_privacy_migration", file)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE user_voices (id VARCHAR PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE projects (id VARCHAR PRIMARY KEY)"))
        connection.execute(text("INSERT INTO user_voices VALUES ('existing')"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        columns = {
            column["name"]: column for column in inspect(connection).get_columns("user_voices")
        }
        assert columns["adult_authorization"]["nullable"] is True
        assert (
            connection.execute(text("SELECT adult_authorization FROM user_voices")).scalar() is None
        )
        assert connection.execute(text("SELECT id FROM user_voices")).scalar() == "existing"


@pytest.mark.asyncio
async def test_revocation_blocks_queued_and_new_generation_but_allows_review(auth_client):
    from fastapi import HTTPException

    from app.models import JobType
    from app.services import jobs
    from app.workers import runner

    pid = auth_client.post("/v1/projects", json={}).json()["id"]
    db = _db(auth_client)
    try:
        project = db.get(Project, uuid.UUID(pid))
        db.add(
            Asset(
                project_id=project.id,
                kind="photo",
                storage_key=f"projects/{pid}/photo/p.jpg",
                meta={"adult_authorization": {"notice_version": "2026-10-29"}},
            )
        )
        db.commit()
        job = jobs.enqueue_job(db, user=project.user, project=project, job_type=JobType.AVATAR)
        response = auth_client.post(f"/v1/projects/{pid}/privacy/revoke")
        assert response.status_code == 200 and response.json()["processing_revoked_at"]
        assert auth_client.get(f"/v1/projects/{pid}").status_code == 200
        with pytest.raises(HTTPException) as blocked:
            jobs.enqueue_job(db, user=project.user, project=project, job_type=JobType.EBOOK)
        assert blocked.value.status_code == 403
        await runner.process_job(db, job)
        assert job.status == "FAILED"
        assert "autorização" in job.error
        assert (
            auth_client.post(
                f"/v1/projects/{pid}/privacy/authorize", json=AUTHORIZATION
            ).status_code
            == 204
        )
        assert auth_client.get(f"/v1/projects/{pid}").json()["processing_revoked_at"] is None
    finally:
        db.close()


def test_old_voice_is_not_used_without_a_recorded_adult_authorization(auth_client):
    from fastapi import HTTPException

    from app.workers.handlers.narrated import _resolve_elevenlabs_voice_id

    user_id = uuid.UUID(auth_client.get("/v1/auth/me").json()["id"])
    db = _db(auth_client)
    try:
        voice = UserVoice(
            user_id=user_id,
            name="Adult",
            elevenlabs_voice_id="own-voice",
            sample_storage_key="private.mp3",
            mime_type="audio/mpeg",
            is_default=True,
        )
        db.add(voice)
        db.commit()
        with pytest.raises(HTTPException) as blocked:
            _resolve_elevenlabs_voice_id(db, user_id, {})
        assert blocked.value.status_code == 403
        voice.adult_authorization = {"notice_version": "2026-10-29"}
        db.commit()
        assert _resolve_elevenlabs_voice_id(db, user_id, {}) == "own-voice"
    finally:
        db.close()


def test_automatic_cleanup_applies_the_approved_90_day_rule(auth_client, monkeypatch, tmp_path):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy.orm import sessionmaker

    from app.models import PrintOrder
    from app.services.privacy_retention import cleanup_abandoned_projects

    monkeypatch.setattr(settings, "storage_local_dir", str(tmp_path))
    monkeypatch.setattr(storage, "_internal_client", lambda: None)
    ids = [auth_client.post("/v1/projects", json={}).json()["id"] for _ in range(3)]
    db = _db(auth_client)
    try:
        old = datetime.now(UTC) - timedelta(days=120)
        for pid in ids:
            project = db.get(Project, uuid.UUID(pid))
            project.created_at = old
            project.last_accessed_at = old
        db.get(Project, uuid.UUID(ids[1])).last_accessed_at = datetime.now(UTC)
        db.add(PrintOrder(project_id=uuid.UUID(ids[2]), code="KEEP-PAID", payment_status="paid"))
        db.commit()
        factory = sessionmaker(bind=db.get_bind(), autoflush=False)
    finally:
        db.close()
    monkeypatch.setattr("app.database.SessionLocal", factory)
    assert cleanup_abandoned_projects() == 1
    assert auth_client.get(f"/v1/projects/{ids[0]}").status_code == 404
    assert auth_client.get(f"/v1/projects/{ids[1]}").status_code == 200
    assert auth_client.get(f"/v1/projects/{ids[2]}").status_code == 200
