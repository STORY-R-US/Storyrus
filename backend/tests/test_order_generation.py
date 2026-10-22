"""Owner regeneration keeps the existing order and story, and reports provenance."""

from datetime import UTC, datetime, timedelta

from app.config import settings
from app.models import Asset, Job, OrderTicket, Project, User
from tests.test_usage import _session


def _order(auth_client):
    db = _session(auth_client)
    try:
        user = db.query(User).filter_by(email="auth@example.com").one()
        project = Project(user_id=user.id, child_name="Lia", story_text="A história original.")
        db.add(project)
        db.flush()
        ticket = OrderTicket(project_id=project.id, summary="Livro\nNome: Lia")
        db.add(ticket)
        db.add(Asset(project_id=project.id, kind="photo", storage_key="photo.jpg"))
        db.commit()
        return ticket.id, project.id
    finally:
        db.close()


def test_regenerate_uses_same_order_and_reuses_story(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "usage_dashboard_password", "owner-test")
    monkeypatch.setattr(settings, "offline_fallback", False)
    ticket_id, project_id = _order(auth_client)
    headers = {"X-Usage-Password": "owner-test"}
    url = f"/v1/usage/orders/{ticket_id}/generate"
    first = auth_client.post(url, headers=headers)
    assert first.status_code == 202, first.text
    again = auth_client.post(url, headers=headers)
    assert again.json()["job_id"] == first.json()["job_id"]
    db = _session(auth_client)
    try:
        assert db.query(OrderTicket).count() == 1
        assert db.get(Project, project_id).story_text == "A história original."
        job = db.query(Job).one()
        assert job.type == "AVATAR"
        assert job.result["payload"] == {"preview_chain": True, "reuse_story": True}
    finally:
        db.close()


def test_master_book_order_starts_preview_not_avatar(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "usage_dashboard_password", "owner-test")
    monkeypatch.setattr(settings, "offline_fallback", False)
    ticket_id, project_id = _order(auth_client)
    db = _session(auth_client)
    try:
        project = db.get(Project, project_id)
        project.book_profile = {"version": 1, "stage": "ficha", "languages": ["pt-BR"]}
        db.commit()
    finally:
        db.close()
    result = auth_client.post(
        f"/v1/usage/orders/{ticket_id}/generate",
        headers={"X-Usage-Password": "owner-test"},
    )
    assert result.status_code == 202, result.text
    db = _session(auth_client)
    try:
        job = db.query(Job).one()
        assert job.type == "EBOOK"
        assert job.result["payload"]["master_preview"] is True
        assert job.result["payload"]["preview_chain"] is True
    finally:
        db.close()


def _preview_files(db, project_id):
    for kind, key in (
        ("cover", "cover.png"),
        ("page_image", "page.png"),
        ("in_hand", "hand.png"),
    ):
        db.add(Asset(project_id=project_id, kind=kind, storage_key=key))


def test_story_failure_keeps_saved_preview(auth_client):
    ticket_id, project_id = _order(auth_client)
    db = _session(auth_client)
    try:
        now = datetime.now(UTC)
        _preview_files(db, project_id)
        db.add(
            Job(
                project_id=project_id,
                type="EBOOK",
                status="DONE",
                cost_usd=0.2,
                result={"image_provider": "openai", "preview_complete": True},
                created_at=now - timedelta(minutes=2),
            )
        )
        db.add(
            Job(
                project_id=project_id,
                type="STORY",
                status="FAILED",
                error="OpenAI 429: credit_balance_exhausted",
                created_at=now,
            )
        )
        db.commit()
    finally:
        db.close()
    orders = auth_client.get("/v1/usage/orders/mine").json()
    order = next(item for item in orders if item["id"] == str(ticket_id))
    assert order["generation_status"] == "ready"
    assert "credit_balance_exhausted" in order["generation_error"]
    assert {item["kind"] for item in order["book_files"]} >= {"cover", "page_image", "in_hand"}


def test_finished_story_reports_preview_ready(auth_client):
    ticket_id, project_id = _order(auth_client)
    db = _session(auth_client)
    try:
        _preview_files(db, project_id)
        db.add(
            Job(
                project_id=project_id,
                type="STORY",
                status="DONE",
                created_at=datetime.now(UTC),
            )
        )
        db.commit()
    finally:
        db.close()
    orders = auth_client.get("/v1/usage/orders/mine").json()
    order = next(item for item in orders if item["id"] == str(ticket_id))
    assert order["generation_status"] == "ready"
    assert order["generation_error"] is None


def test_failed_preview_without_images_stays_failed(auth_client):
    ticket_id, project_id = _order(auth_client)
    db = _session(auth_client)
    try:
        db.add(
            Job(
                project_id=project_id,
                type="EBOOK",
                status="FAILED",
                error="OpenAI 429: insufficient_quota",
                created_at=datetime.now(UTC),
            )
        )
        db.commit()
    finally:
        db.close()
    orders = auth_client.get("/v1/usage/orders/mine").json()
    order = next(item for item in orders if item["id"] == str(ticket_id))
    assert order["generation_status"] == "failed"
    assert order["generation_error"] == "OpenAI 429: insufficient_quota"


def test_regeneration_rejects_demo_mode(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "usage_dashboard_password", "owner-test")
    ticket_id, _ = _order(auth_client)
    result = auth_client.post(
        f"/v1/usage/orders/{ticket_id}/generate",
        headers={"X-Usage-Password": "owner-test"},
    )
    assert result.status_code == 503


def test_preview_status_reports_demo_and_partial_truthfully(auth_client, monkeypatch):
    ticket_id, project_id = _order(auth_client)
    db = _session(auth_client)
    try:
        job = Job(
            project_id=project_id,
            type="EBOOK",
            status="DONE",
            cost_usd=0,
            result={"payload": {"preview_chain": True}, "image_provider": "demo"},
        )
        db.add(job)
        db.commit()
        orders = auth_client.get("/v1/usage/orders/mine").json()
        assert orders[0]["generation_status"] == "demo"
        job.result = {
            "image_provider": "openai",
            "image_model": "gpt-image-1",
            "preview_complete": False,
        }
        job.cost_usd = 0.08
        db.commit()
        orders = auth_client.get("/v1/usage/orders/mine").json()
        assert orders[0]["generation_status"] == "partial"
        assert orders[0]["image_provider"] == "openai"
    finally:
        db.close()
