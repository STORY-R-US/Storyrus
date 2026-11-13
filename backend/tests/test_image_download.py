import io
import uuid

from sqlalchemy import func, select

from app import storage
from app.database import get_db
from app.main import app
from app.models import Asset, AssetKind, Job, Project
from tests.conftest import signup_and_verify


def test_image_download_uses_saved_visible_output_without_jobs(auth_client, monkeypatch):
    client = auth_client
    pid = client.post("/v1/projects", json={"title": "Lia"}).json()["id"]
    generator = app.dependency_overrides[get_db]()
    db = next(generator)
    project = db.get(Project, uuid.UUID(pid))
    project.book_profile = {"editorial": {"version": "current"}}
    image = Asset(
        project_id=project.id,
        kind=AssetKind.COVER.value,
        storage_key="clean",
        meta={
            "workflow": 1,
            "role": "01_CAPA",
            "editorial": {"version": "current"},
            "filename": "Lia-coração.png",
            "watermark_key": "marked",
        },
    )
    photo = Asset(project_id=project.id, kind=AssetKind.PHOTO.value, storage_key="private", meta={})
    db.add_all([image, photo])
    db.commit()
    monkeypatch.setattr("app.routers.projects.display_key", lambda _db, _asset: "marked")
    streams, keys = [], []

    from contextlib import contextmanager

    @contextmanager
    def reader(key):
        keys.append(key)
        stream = io.BytesIO(b"saved-png" * 20000)
        streams.append(stream)
        try:
            yield stream
        finally:
            stream.close()

    monkeypatch.setattr(storage, "open_reader", reader)
    path = f"/v1/projects/{pid}/assets/{image.id}/download"
    for _ in range(2):
        response = client.get(path)
        assert response.status_code == 200
        assert response.content == b"saved-png" * 20000
        assert (
            response.headers["content-disposition"]
            == "attachment; filename*=UTF-8''Lia-cora%C3%A7%C3%A3o.png"
        )
        assert response.headers["cache-control"] == "private, no-store"
    assert keys == ["marked", "marked"]
    assert all(stream.closed for stream in streams)
    assert db.scalar(select(func.count()).select_from(Job)) == 0
    assert client.get(f"/v1/projects/{pid}/assets/{photo.id}/download").status_code == 404
    image.meta = {**image.meta, "archived": True}
    db.commit()
    assert client.get(path).status_code == 404
    image.meta = {**image.meta, "archived": False, "editorial": {"version": "old"}}
    db.commit()
    assert client.get(path).status_code == 404
    other = signup_and_verify(client, "download-other@example.com")
    assert client.get(path, headers={"Authorization": f"Bearer {other}"}).status_code == 404
    generator.close()
