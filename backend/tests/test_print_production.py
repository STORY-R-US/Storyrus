"""Arquivos de produção, pacote, frete e checkout do impresso."""

from __future__ import annotations

import io
import json
import uuid
import zipfile
from datetime import UTC, datetime

import httpx
import pytest
from PIL import Image
from pypdf import PdfReader

from app import storage
from app.config import settings
from app.database import get_db
from app.models import Asset, AssetKind, Project
from app.printkit.files import build_print_pdfs
from app.printkit.gateway import (
    ChargeResult,
    GatewayRejected,
    PaymentNotice,
    register_gateway,
    unregister_gateway,
)
from app.printkit.shipping import LabelResult
from app.printkit.spec import PrintSpec, PrintSpecIncomplete


@pytest.fixture(autouse=True)
def _local_disk(monkeypatch):
    monkeypatch.setattr(settings, "storage_access_key", None)
    monkeypatch.setattr(settings, "storage_secret_key", None)
    storage._client.cache_clear()
    yield
    storage._client.cache_clear()


def _session(client):
    gen = client.app.dependency_overrides[get_db]()
    return next(gen)


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), (20, 80, 160)).save(buf, format="PNG")
    return buf.getvalue()


def _filled_spec() -> PrintSpec:
    return PrintSpec(
        bleed_mm=3,
        safety_mm=5,
        spine_mm=12,
        score_mm=8,
        pdf_x="PDF/X-4",
        color_profile="FOGRA39",
        filename_pattern="{code}-{part}.pdf",
    )


def _apply_spec(monkeypatch) -> None:
    spec = _filled_spec()
    monkeypatch.setattr(settings, "print_bleed_mm", spec.bleed_mm)
    monkeypatch.setattr(settings, "print_safety_mm", spec.safety_mm)
    monkeypatch.setattr(settings, "print_spine_mm", spec.spine_mm)
    monkeypatch.setattr(settings, "print_score_mm", spec.score_mm)
    monkeypatch.setattr(settings, "print_pdf_x", spec.pdf_x)
    monkeypatch.setattr(settings, "print_color_profile", spec.color_profile)
    monkeypatch.setattr(settings, "print_filename_pattern", spec.filename_pattern)
    monkeypatch.setattr(settings, "print_allow_p_hardcover", False)
    monkeypatch.setattr(settings, "print_gateway", "")
    monkeypatch.setattr(settings, "print_price_p_cents", 15700)
    monkeypatch.setattr(settings, "print_price_m_cents", 17700)


def _blank_spec(monkeypatch) -> None:
    for name in (
        "print_bleed_mm",
        "print_safety_mm",
        "print_spine_mm",
        "print_score_mm",
        "print_pdf_x",
        "print_color_profile",
        "print_filename_pattern",
    ):
        monkeypatch.setattr(settings, name, None)
    monkeypatch.setattr(settings, "print_allow_p_hardcover", False)
    monkeypatch.setattr(settings, "print_gateway", "")
    monkeypatch.setattr(settings, "print_price_p_cents", 15700)
    monkeypatch.setattr(settings, "print_price_m_cents", 17700)


def _pt(mm: float) -> float:
    return mm * 72.0 / 25.4


def _ready(auth_client, *, size="M", cover="soft", pages=2) -> str:
    pid = auth_client.post(
        "/v1/projects",
        json={"book_size": size, "cover_type": cover, "style": "realistic"},
    ).json()["id"]
    db = _session(auth_client)
    try:
        project = db.get(Project, uuid.UUID(pid))
        project.ebook_url = "ebook.pdf"
        project.book_approved_at = datetime.now(UTC)
        blob = _png()
        for index in range(pages):
            key = storage.new_key(project.id, "page_image", "png")
            storage.put_bytes(key, blob, "image/png")
            db.add(
                Asset(
                    project_id=project.id,
                    kind=AssetKind.PAGE_IMAGE.value,
                    storage_key=key,
                    meta={"page": index},
                )
            )
        db.commit()
    finally:
        db.close()
    return pid


def _address(auth_client, pid: str):
    return auth_client.put(
        f"/v1/projects/{pid}/print-order/address",
        json={
            "recipient_name": "Ana",
            "postal_code": "01310-100",
            "street": "Av. Paulista",
            "number": "1000",
            "district": "Bela Vista",
            "city": "São Paulo",
            "state": "sp",
        },
    )


class _FakeGateway:
    name = "fake"

    def create_charge(
        self, *, order_code: str, amount_cents: int, installments: int
    ) -> ChargeResult:
        assert amount_cents > 0
        assert installments == 3
        return ChargeResult(
            provider="fake",
            reference=f"pay-{order_code}",
            checkout_url="https://pay.test/livro",
        )

    def parse_webhook(self, body: bytes, signature: str | None) -> PaymentNotice:
        if signature != "ok":
            raise GatewayRejected("assinatura")
        data = json.loads(body)
        return PaymentNotice(reference=data["reference"], paid=bool(data.get("paid")))


def _pages(count: int = 16) -> list[Image.Image]:
    return [Image.new("RGB", (32, 32), (20, 80, 160)) for _ in range(count)]


def _span_mm(box) -> tuple[float, float]:
    left, bottom, right, top = (float(v) for v in box)
    return (right - left) * 25.4 / 72, (top - bottom) * 25.4 / 72


def test_blank_spec_refuses_production_pdf():
    spec = PrintSpec()
    try:
        build_print_pdfs(
            order_code="SR-TESTE001",
            book_size="M",
            cover_type="soft",
            spec=spec,
            interior_pages=[_png()],
        )
        raise AssertionError("spec vazia não pode gerar arquivo")
    except PrintSpecIncomplete as exc:
        assert "bleed_mm" in exc.gaps
        assert "score_mm" in exc.gaps


def test_pdfs_share_the_order_code_and_the_cover_width():
    spec = _filled_spec()
    code = "SR-AB12CD34"
    cover, interior = build_print_pdfs(
        order_code=code,
        book_size="M",
        cover_type="soft",
        spec=spec,
        interior_pages=[_png(), _png()],
    )
    cover_pdf = PdfReader(io.BytesIO(cover))
    interior_pdf = PdfReader(io.BytesIO(interior))
    assert cover_pdf.metadata.title == code
    assert interior_pdf.metadata.title == code
    assert code in (cover_pdf.pages[0].extract_text() or "")
    assert len(interior_pdf.pages) == 2
    assert abs(float(cover_pdf.pages[0].mediabox.width) - _pt(414)) < 0.2
    assert abs(float(interior_pdf.pages[0].mediabox.width) - _pt(206)) < 0.2


def test_print_request_without_spec_does_not_publish_files(auth_client, monkeypatch):
    _blank_spec(monkeypatch)
    pid = _ready(auth_client)
    r = auth_client.post(f"/v1/projects/{pid}/print-request")
    assert r.status_code == 200, r.text
    assert r.json()["print_status"] == "awaiting_spec"
    order = auth_client.get(f"/v1/projects/{pid}/print-order")
    assert order.status_code == 200
    body = order.json()
    assert body["code"].startswith("SR-")
    assert body["book_price_cents"] == 17700
    assert "bleed_mm" in body["block_reason"]
    monkeypatch.setattr(settings, "usage_dashboard_password", "segredo")
    packed = auth_client.get(
        f"/v1/print-orders/{body['id']}/package",
        headers={"X-Usage-Password": "segredo"},
    )
    assert packed.status_code == 409


def test_package_when_spec_is_filled(auth_client, monkeypatch):
    _apply_spec(monkeypatch)
    monkeypatch.setattr(settings, "usage_dashboard_password", "segredo")
    pid = _ready(auth_client, cover="hard", pages=16)
    opened = auth_client.post(f"/v1/projects/{pid}/print-request")
    assert opened.json()["print_status"] == "files_ready"
    order = auth_client.get(f"/v1/projects/{pid}/print-order").json()
    assert order["book_price_cents"] == 17700
    packed = auth_client.get(
        f"/v1/print-orders/{order['id']}/package",
        headers={"X-Usage-Password": "segredo"},
    )
    assert packed.status_code == 200, packed.text
    archive = zipfile.ZipFile(io.BytesIO(packed.content))
    manifest = json.loads(archive.read("pedido.json"))
    assert manifest["quantity"] == 1
    assert manifest["cover_type"] == "hard"
    assert manifest["code"] == order["code"]
    assert archive.read(manifest["files"]["capa"])[:4] == b"%PDF"
    assert archive.read(manifest["files"]["miolo"])[:4] == b"%PDF"
    sent = auth_client.post(
        f"/v1/print-orders/{order['id']}/validation",
        json={"status": "sent_for_validation"},
        headers={"X-Usage-Password": "segredo"},
    )
    assert sent.status_code == 200
    approved = auth_client.post(
        f"/v1/print-orders/{order['id']}/validation",
        json={"status": "approved"},
        headers={"X-Usage-Password": "segredo"},
    )
    assert approved.json()["status"] == "approved"
    again = auth_client.post(
        f"/v1/print-orders/{order['id']}/validation",
        json={"status": "rejected"},
        headers={"X-Usage-Password": "segredo"},
    )
    assert again.status_code == 409


def test_small_hardcover_stays_held(auth_client, monkeypatch):
    _apply_spec(monkeypatch)
    pid = _ready(auth_client, size="P", cover="hard")
    opened = auth_client.post(f"/v1/projects/{pid}/print-request")
    assert opened.json()["print_status"] == "held"
    order = auth_client.get(f"/v1/projects/{pid}/print-order").json()
    assert "15" in order["block_reason"]


def test_cover_type_does_not_change_the_book_price(auth_client, monkeypatch):
    _apply_spec(monkeypatch)
    soft = _ready(auth_client, size="P", cover="soft")
    hard = _ready(auth_client, size="P", cover="hard")
    auth_client.post(f"/v1/projects/{soft}/print-request")
    auth_client.post(f"/v1/projects/{hard}/print-request")
    soft_price = auth_client.get(f"/v1/projects/{soft}/print-order").json()["book_price_cents"]
    hard_price = auth_client.get(f"/v1/projects/{hard}/print-order").json()["book_price_cents"]
    assert soft_price == hard_price == 15700


def test_freight_refuses_when_melhor_envio_is_not_configured(auth_client, monkeypatch):
    _blank_spec(monkeypatch)
    monkeypatch.setattr(settings, "melhor_envio_token", "")
    pid = _ready(auth_client)
    auth_client.post(f"/v1/projects/{pid}/print-request")
    saved = _address(auth_client, pid)
    assert saved.status_code == 200, saved.text
    quoted = auth_client.post(f"/v1/projects/{pid}/print-order/freight")
    assert quoted.status_code == 409
    assert "melhor_envio_token" in quoted.json()["detail"]


def test_freight_keeps_a_missing_deadline(auth_client, monkeypatch):
    _blank_spec(monkeypatch)
    monkeypatch.setattr(settings, "melhor_envio_token", "token")
    monkeypatch.setattr(settings, "melhor_envio_from_postal_code", "01001000")
    monkeypatch.setattr(settings, "print_package_weight_g", 400)
    monkeypatch.setattr(settings, "print_package_height_cm", 3)
    monkeypatch.setattr(settings, "print_package_width_cm", 21)
    monkeypatch.setattr(settings, "print_package_length_cm", 21)

    def _post(url, payload):
        assert payload["package"]["weight"] == 0.4
        return httpx.Response(
            200,
            json=[
                {"id": 1, "name": "PAC", "price": "19.20", "delivery_time": 8},
                {
                    "id": 2,
                    "name": "SEDEX",
                    "custom_price": "30.00",
                    "price": "40.00",
                    "delivery_time": None,
                },
                {"id": 3, "name": "Erro", "error": "sem cobertura", "price": "1.00"},
            ],
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr("app.printkit.shipping._post", _post)
    pid = _ready(auth_client)
    auth_client.post(f"/v1/projects/{pid}/print-request")
    assert _address(auth_client, pid).status_code == 200
    quoted = auth_client.post(f"/v1/projects/{pid}/print-order/freight")
    assert quoted.status_code == 200, quoted.text
    names = [item["service_name"] for item in quoted.json()["freight_options"]]
    assert names == ["PAC", "SEDEX"]
    chosen = auth_client.post(
        f"/v1/projects/{pid}/print-order/freight/select",
        json={"service_id": 2},
    )
    assert chosen.status_code == 200, chosen.text
    body = chosen.json()
    assert body["freight_price_cents"] == 3000
    assert body["freight_days"] is None


def _freight_ready(monkeypatch):
    monkeypatch.setattr(settings, "melhor_envio_token", "token")
    monkeypatch.setattr(settings, "melhor_envio_from_postal_code", "01001000")
    monkeypatch.setattr(settings, "print_package_weight_g", 400)
    monkeypatch.setattr(settings, "print_package_height_cm", 3)
    monkeypatch.setattr(settings, "print_package_width_cm", 21)
    monkeypatch.setattr(settings, "print_package_length_cm", 21)
    monkeypatch.setattr(
        "app.printkit.shipping._post",
        lambda url, payload: httpx.Response(
            200,
            json=[{"id": 1, "name": "PAC", "price": "10.00", "delivery_time": 5}],
            request=httpx.Request("POST", url),
        ),
    )


def test_quantity_is_chosen_at_checkout_and_multiplies_the_book(auth_client, monkeypatch):
    _apply_spec(monkeypatch)
    _freight_ready(monkeypatch)
    monkeypatch.setattr(settings, "print_gateway", "fake")
    register_gateway(_FakeGateway())
    try:
        pid = _ready(auth_client)
        auth_client.post(f"/v1/projects/{pid}/print-request")
        one = auth_client.put(f"/v1/projects/{pid}/print-order/quantity", json={"quantity": 1})
        assert one.status_code == 200
        assert one.json()["quantity"] == 1
        copies = auth_client.put(f"/v1/projects/{pid}/print-order/quantity", json={"quantity": 4})
        assert copies.json()["quantity"] == 4
        package = auth_client.put(f"/v1/projects/{pid}/print-order/quantity", json={"quantity": 12})
        assert package.json()["quantity"] == 12
        assert (
            auth_client.put(
                f"/v1/projects/{pid}/print-order/quantity", json={"quantity": 0}
            ).status_code
            == 422
        )
        _address(auth_client, pid)
        auth_client.post(f"/v1/projects/{pid}/print-order/freight")
        auth_client.post(f"/v1/projects/{pid}/print-order/freight/select", json={"service_id": 1})
        paid = auth_client.post(
            f"/v1/projects/{pid}/print-order/checkout", json={"installments": 3}
        )
        assert paid.status_code == 200, paid.text
        assert paid.json()["amount_cents"] == 17700 * 12 + 1000
        locked = auth_client.put(f"/v1/projects/{pid}/print-order/quantity", json={"quantity": 2})
        assert locked.status_code == 409
    finally:
        unregister_gateway("fake")


def test_checkout_without_gateway(auth_client, monkeypatch):
    _apply_spec(monkeypatch)
    _freight_ready(monkeypatch)
    pid = _ready(auth_client)
    auth_client.post(f"/v1/projects/{pid}/print-request")
    _address(auth_client, pid)
    auth_client.post(f"/v1/projects/{pid}/print-order/freight")
    auth_client.post(f"/v1/projects/{pid}/print-order/freight/select", json={"service_id": 1})
    unpaid = auth_client.post(f"/v1/projects/{pid}/print-order/checkout", json={"installments": 2})
    assert unpaid.status_code == 409
    assert "Gateway" in unpaid.json()["detail"]


def test_paid_webhook_buys_the_label(auth_client, monkeypatch):
    _apply_spec(monkeypatch)
    _freight_ready(monkeypatch)
    monkeypatch.setattr(settings, "print_gateway", "fake")
    bought: list[str] = []

    def _buy(order):
        bought.append(order.code)
        return LabelResult(tracking="AA123BR", url=None)

    monkeypatch.setattr("app.printkit.service.buy_label", _buy)
    register_gateway(_FakeGateway())
    try:
        pid = _ready(auth_client)
        auth_client.post(f"/v1/projects/{pid}/print-request")
        _address(auth_client, pid)
        auth_client.post(f"/v1/projects/{pid}/print-order/freight")
        auth_client.post(f"/v1/projects/{pid}/print-order/freight/select", json={"service_id": 1})
        paid = auth_client.post(
            f"/v1/projects/{pid}/print-order/checkout", json={"installments": 3}
        )
        assert paid.status_code == 200, paid.text
        body = paid.json()
        assert body["amount_cents"] == 17700 + 1000
        assert body["checkout_url"] == "https://pay.test/livro"
        assert bought == []
        missing = auth_client.post(
            "/v1/webhooks/print-payment",
            json={"reference": "pay-ausente", "paid": True},
            headers={"X-Print-Signature": "ok"},
        )
        assert missing.status_code == 404
        hook = auth_client.post(
            "/v1/webhooks/print-payment",
            json={"reference": f"pay-{body['code']}", "paid": True},
            headers={"X-Print-Signature": "ok"},
        )
        assert hook.status_code == 200, hook.text
        assert bought == [body["code"]]
        tracked = auth_client.get(f"/v1/projects/{pid}/print-order").json()
        assert tracked["tracking_code"] == "AA123BR"
        assert tracked["payment_status"] == "paid"
    finally:
        unregister_gateway("fake")
