"""The preview must never authorize printing or bypass the payment gate."""

import uuid

import pytest
from sqlalchemy import select

from app.database import get_db
from app.models import Job, Project, User, _now
from app.printkit.service import advance_validation, fulfill_payment, get_print_order
from app.services import purchase_flow


def session(client):
    return next(client.app.dependency_overrides[get_db]())


def preview(client):
    result = client.post(
        "/v1/projects",
        json={
            "title": "Lila e as estrelas",
            "theme_description": "Aventura no espaço",
            "book_size": "M",
            "cover_type": "soft",
        },
    )
    assert result.status_code == 201
    pid = result.json()["id"]
    with session(client) as db:
        p = db.get(Project, uuid.UUID(pid))
        p.story_text = "Título: Lila e as estrelas\n\nPágina 1: Uma estrela brilhou."
        p.character_ref = {"storage_key": "avatar.png"}
        p.character_approved_at = _now()
        p.ebook_url = "preview.pdf"
        purchase_flow.update(p, preview_ready_at=purchase_flow.timestamp(), stage="preview_ready")
        db.commit()
    return pid


def approve(client):
    pid = preview(client)
    r = client.post(f"/v1/projects/{pid}/preview/approve")
    assert r.status_code == 200, r.text
    return pid


def test_preview_approval_opens_quotation_without_approving_book(auth_client):
    pid = approve(auth_client)
    p = auth_client.get(f"/v1/projects/{pid}").json()
    assert p["purchase_flow"]["preview_approved_at"]
    assert p["book_approved_at"] is None
    order = auth_client.get(f"/v1/projects/{pid}/print-order").json()
    assert order["status"] == "awaiting_payment"
    assert order["payment_status"] == "unpaid"
    assert not order["checkout_available"]
    assert auth_client.post(f"/v1/projects/{pid}/quotation").json()["purchase_flow"]["quoted_at"]
    assert auth_client.post(f"/v1/projects/{pid}/book/generate").status_code == 409
    assert auth_client.post(f"/v1/projects/{pid}/ebook").status_code == 409
    assert auth_client.post(f"/v1/projects/{pid}/book/approve").status_code == 409


def test_changes_save_all_fields_and_require_new_preview_approval(auth_client):
    pid = approve(auth_client)
    r = auth_client.put(
        f"/v1/projects/{pid}/preview/changes",
        json={
            "title": "Lila e a lua",
            "theme_description": "Amizade na lua",
            "story_text": "Título: Antigo\n\nPágina 1: A lua sorriu.",
            "photo_notes": "Preservar os óculos azuis",
        },
    )
    assert r.status_code == 202, r.text
    p = auth_client.get(f"/v1/projects/{pid}").json()
    assert p["story_text"].startswith("Título: Lila e a lua")
    assert p["purchase_flow"]["theme_description"] == "Amizade na lua"
    assert p["purchase_flow"]["photo_notes"] == "Preservar os óculos azuis"
    assert p["purchase_flow"]["preview_approved_at"] is None
    assert auth_client.post(f"/v1/projects/{pid}/preview/approve").status_code == 409


def test_paid_callback_enqueues_only_once_and_waits_for_final_review(auth_client):
    pid = approve(auth_client)
    with session(auth_client) as db:
        order = get_print_order(db, uuid.UUID(pid))
        fulfill_payment(db, order)
        fulfill_payment(db, order)
        db.commit()
        queued = db.scalars(select(Job).where(Job.project_id == uuid.UUID(pid))).all()
        assert len(queued) == 1
        assert queued[0].result["payload"]["purchase_full_book"]
        assert order.payment_status == "paid"
        assert not order.tracking_code
        with pytest.raises(ValueError):
            advance_validation(order, "sent_for_validation")
    assert auth_client.post(f"/v1/projects/{pid}/book/approve").status_code == 409
    assert auth_client.post(f"/v1/projects/{pid}/preview").status_code == 409
    assert (
        auth_client.post(
            f"/v1/projects/{pid}/story/text", json={"story_text": "Outra história"}
        ).status_code
        == 409
    )


def test_owner_confirms_payment_and_starts_the_book(auth_client):
    pid = approve(auth_client)
    saved = auth_client.put(
        f"/v1/projects/{pid}/print-order/address",
        json={
            "recipient_name": "Ana",
            "postal_code": "01310100",
            "street": "Av. Paulista",
            "number": "1000",
            "district": "Bela Vista",
            "city": "São Paulo",
            "state": "SP",
        },
    )
    assert saved.status_code == 200, saved.text
    refused = auth_client.post(f"/v1/projects/{pid}/print-order/confirm-payment")
    assert refused.status_code == 403
    with session(auth_client) as db:
        user = db.scalar(select(User).where(User.email == "auth@example.com"))
        user.is_admin = True
        db.commit()
    confirmed = auth_client.post(f"/v1/projects/{pid}/print-order/confirm-payment")
    assert confirmed.status_code == 200, confirmed.text
    body = confirmed.json()
    assert body["payment_status"] == "paid"
    assert body["amount_cents"] == 17700
    project = auth_client.get(f"/v1/projects/{pid}").json()
    assert project["purchase_flow"]["stage"] == "generating_book"
    with session(auth_client) as db:
        order = get_print_order(db, uuid.UUID(pid))
        assert order.payment_provider == "manual"
        queued = db.scalars(select(Job).where(Job.project_id == uuid.UUID(pid))).all()
        assert len(queued) == 1
        assert queued[0].result["payload"]["purchase_full_book"]


def test_customer_can_only_access_own_orders(auth_client):
    pid = approve(auth_client)
    from conftest import signup_and_verify

    token = signup_and_verify(auth_client, "other-purchase@example.com")
    auth_client.headers["Authorization"] = f"Bearer {token}"
    assert auth_client.get("/v1/projects").json() == []
    assert auth_client.post(f"/v1/projects/{pid}/preview/approve").status_code == 404
    assert auth_client.get(f"/v1/projects/{pid}/print-order").status_code == 404


def test_quantity_and_address_changes_clear_old_shipping_price(auth_client):
    pid = approve(auth_client)
    with session(auth_client) as db:
        order = get_print_order(db, uuid.UUID(pid))
        order.freight_price_cents = 2000
        order.freight_service_id = 1
        db.commit()
    r = auth_client.put(f"/v1/projects/{pid}/print-order/quantity", json={"quantity": 3})
    assert r.status_code == 200
    assert r.json()["freight_price_cents"] is None
    assert r.json()["quantity"] == 3


def test_paid_book_retry_has_one_job_per_attempt(auth_client):
    pid = approve(auth_client)
    with session(auth_client) as db:
        order = get_print_order(db, uuid.UUID(pid))
        fulfill_payment(db, order)
        job = db.scalar(select(Job).where(Job.project_id == uuid.UUID(pid)))
        job.status = "FAILED"
        db.commit()
    first = auth_client.post(f"/v1/projects/{pid}/book/generate")
    second = auth_client.post(f"/v1/projects/{pid}/book/generate")
    assert first.status_code == second.status_code == 202
    assert first.json()["job_id"] == second.json()["job_id"]
    with session(auth_client) as db:
        assert len(db.scalars(select(Job).where(Job.project_id == uuid.UUID(pid))).all()) == 2


def test_printer_keeps_the_shipment_after_approval(auth_client):
    from app.printkit import service

    pid = approve(auth_client)
    with session(auth_client) as db:
        order = get_print_order(db, uuid.UUID(pid))
        order.payment_status = "paid"
        order.project.book_approved_at = _now()
        order.status = "approved"
        service.prepare_shipping_label(db, order)
        assert order.tracking_code is None
        assert order.label_error is None


def test_final_approval_requires_paid_complete_book(auth_client, monkeypatch):
    called = {}

    def fake_notify(_db, project, order):
        called["code"] = order.code
        called["ebook"] = project.ebook_url
        return True

    monkeypatch.setattr("app.services.transactional_email.notify_print_shop", fake_notify)
    pid = approve(auth_client)
    with session(auth_client) as db:
        p = db.get(Project, uuid.UUID(pid))
        purchase_flow.update(p, full_book_ready_at=purchase_flow.timestamp(), stage="book_ready")
        db.commit()
    assert auth_client.post(f"/v1/projects/{pid}/book/approve").status_code == 409
    assert called == {}
    with session(auth_client) as db:
        get_print_order(db, uuid.UUID(pid)).payment_status = "paid"
        db.commit()
    r = auth_client.post(f"/v1/projects/{pid}/book/approve")
    assert r.status_code == 200, r.text
    assert r.json()["book_approved_at"]
    assert r.json()["purchase_flow"]["stage"] == "production_approved"
    assert called["ebook"] == "preview.pdf"
    assert called["code"].startswith("SR-")


@pytest.mark.asyncio
async def test_paid_generation_contains_every_story_page(auth_client, monkeypatch):
    from io import BytesIO

    from pypdf import PdfReader
    from test_workers import FakeImage

    from app import storage
    from app.workers import handlers
    from app.workers.handlers import ebook
    from app.workers.handlers.common import _offline_png

    store = {"avatar.png": _offline_png("Avatar", palette=((230, 240, 255), (255, 255, 255)))}
    monkeypatch.setattr(storage, "get_bytes", lambda key: store[key])
    monkeypatch.setattr(storage, "put_bytes", lambda key, blob, mime: store.update({key: blob}))
    monkeypatch.setattr(handlers, "get_image_provider", lambda: FakeImage())

    async def briefs(*args, **kwargs):
        return [{"scene": "Uma estrela"} for _ in range(4)]

    monkeypatch.setattr(ebook, "ensure_page_briefs", briefs)
    pid = approve(auth_client)
    with session(auth_client) as db:
        p = db.get(Project, uuid.UUID(pid))
        p.story_text = "Título: Lila e as estrelas\n\n" + "\n\n".join(
            f"Página {n}: A estrela número {n} brilhou para Lila." for n in range(1, 5)
        )
        order = get_print_order(db, p.id)
        order.payment_status = "paid"
        job = purchase_flow.enqueue_paid_book(db, order)
        await ebook.handle_ebook(db, job)
        pdf = PdfReader(BytesIO(store[p.ebook_url]))
        text = " ".join(page.extract_text() or "" for page in pdf.pages)
        assert "número 4" in text
        assert len(pdf.pages) > 4
        assert p.purchase_flow["full_book_ready_at"]
        assert p.book_approved_at is None
