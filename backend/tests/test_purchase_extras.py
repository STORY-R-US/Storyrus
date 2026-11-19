"""E-book e história animada: extras do impresso e compra só digital."""

import uuid

import pytest
from sqlalchemy import select
from test_purchase_flow import approve, session

from app.models import Asset, AssetKind, Job, Project, User
from app.printkit.pricing import ebook_delivered, purchase_choice
from app.printkit.service import get_print_order
from app.services import purchase_flow

ADDRESS = {
    "recipient_name": "Ana",
    "postal_code": "01310100",
    "street": "Av. Paulista",
    "number": "1000",
    "district": "Bela Vista",
    "city": "São Paulo",
    "state": "SP",
}


def make_admin(client):
    with session(client) as db:
        user = db.scalar(select(User).where(User.email == "auth@example.com"))
        user.is_admin = True
        db.commit()


def choose(client, pid, **body):
    return client.put(f"/v1/projects/{pid}/print-order/purchase", json=body)


def test_order_shows_prices_and_defaults_to_print_only(auth_client):
    pid = approve(auth_client)
    order = auth_client.get(f"/v1/projects/{pid}/print-order").json()
    assert order["fulfillment"] == "print"
    assert order["extra_ebook"] is False and order["extra_video"] is False
    assert order["items_price_cents"] == 17700
    assert order["prices"] == {
        "extra": {"ebook": 2900, "video": 8900, "bundle": 9900},
        "digital": {"ebook": 11900, "video": 20900, "bundle": 21900},
    }


def test_print_with_both_extras_charges_the_bundle(auth_client):
    pid = approve(auth_client)
    r = choose(auth_client, pid, fulfillment="print", ebook=True, video=True)
    assert r.status_code == 200, r.text
    assert r.json()["items_price_cents"] == 17700 + 9900
    assert (
        auth_client.put(f"/v1/projects/{pid}/print-order/address", json=ADDRESS).status_code == 200
    )
    make_admin(auth_client)
    paid = auth_client.post(f"/v1/projects/{pid}/print-order/confirm-payment")
    assert paid.status_code == 200, paid.text
    assert paid.json()["amount_cents"] == 17700 + 9900
    assert choose(auth_client, pid, fulfillment="print").status_code == 409


def test_digital_only_needs_no_address_and_skips_the_printer(auth_client, monkeypatch):
    called = []
    monkeypatch.setattr(
        "app.services.transactional_email.notify_print_shop",
        lambda _db, project, order: called.append(order.code) or True,
    )
    pid = approve(auth_client)
    assert choose(auth_client, pid, fulfillment="digital").status_code == 409
    r = choose(auth_client, pid, fulfillment="digital", ebook=True)
    assert r.status_code == 200, r.text
    assert r.json()["fulfillment"] == "digital"
    assert r.json()["items_price_cents"] == 11900
    with session(auth_client) as db:
        order = get_print_order(db, uuid.UUID(pid))
        order.recipient_name = None
        order.postal_code = None
        db.commit()
    make_admin(auth_client)
    paid = auth_client.post(f"/v1/projects/{pid}/print-order/confirm-payment")
    assert paid.status_code == 200, paid.text
    assert paid.json()["amount_cents"] == 11900
    with session(auth_client) as db:
        p = db.get(Project, uuid.UUID(pid))
        purchase_flow.update(p, full_book_ready_at=purchase_flow.timestamp(), stage="book_ready")
        for job in p.jobs:
            job.status = "DONE"
        db.commit()
    approved = auth_client.post(f"/v1/projects/{pid}/book/approve")
    assert approved.status_code == 200, approved.text
    assert called == []
    assert approved.json()["print_status"] == "digital_ready"
    with session(auth_client) as db:
        order = get_print_order(db, uuid.UUID(pid))
        assert order.cover_key is None and order.interior_key is None
        assert not db.scalars(
            select(Job).where(Job.project_id == uuid.UUID(pid), Job.type == "VIDEO")
        ).all()


def test_purchased_story_video_is_queued_once(auth_client, monkeypatch):
    monkeypatch.setattr(
        "app.services.transactional_email.notify_print_shop", lambda *_a, **_k: True
    )
    pid = approve(auth_client)
    assert choose(auth_client, pid, fulfillment="digital", video=True).status_code == 200
    make_admin(auth_client)
    assert auth_client.post(f"/v1/projects/{pid}/print-order/confirm-payment").status_code == 200
    with session(auth_client) as db:
        p = db.get(Project, uuid.UUID(pid))
        purchase_flow.update(p, full_book_ready_at=purchase_flow.timestamp(), stage="book_ready")
        for job in p.jobs:
            job.status = "DONE"
        db.commit()
    assert auth_client.post(f"/v1/projects/{pid}/book/approve").status_code == 200
    with session(auth_client) as db:
        order = get_print_order(db, uuid.UUID(pid))
        again = purchase_flow.enqueue_purchased_video(db, order)
        videos = db.scalars(
            select(Job).where(Job.project_id == uuid.UUID(pid), Job.type == "VIDEO")
        ).all()
        assert len(videos) == 1
        assert again.id == videos[0].id
        assert videos[0].result["payload"]["source"] == "story"
        assert videos[0].result["payload"]["duration_s"] == 5


def test_pdf_stays_with_orders_paid_before_the_extras(auth_client):
    pid = approve(auth_client)
    with session(auth_client) as db:
        p = db.get(Project, uuid.UUID(pid))
        assert ebook_delivered(p)
        purchase_flow.update(p, purchase=purchase_choice(p))
        assert not ebook_delivered(p)
        purchase_flow.update(p, purchase={"fulfillment": "print", "ebook": True, "video": False})
        assert ebook_delivered(p)


def test_animated_cover_uses_the_clean_cover_in_the_book_language(auth_client):
    from app.ai_clients.base import ProviderError
    from app.workers.handlers.video import _cover_reference_key

    pid = approve(auth_client)
    with session(auth_client) as db:
        p = db.get(Project, uuid.UUID(pid))
        with pytest.raises(ProviderError):
            _cover_reference_key(db, p)
        p.language = "es"
        for lang in ("pt-BR", "es"):
            db.add(
                Asset(
                    project_id=p.id,
                    kind=AssetKind.COVER.value,
                    storage_key=f"capa-{lang}.png",
                    meta={
                        "workflow": 1,
                        "role": "01_CAPA",
                        "language": lang,
                        "watermark_key": f"marca-{lang}.png",
                    },
                )
            )
        db.commit()
        assert _cover_reference_key(db, p) == "capa-es.png"
