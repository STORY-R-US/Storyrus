"""Stripe Checkout: sessão em BRL e webhook assinado."""

from __future__ import annotations

import json

import pytest

from app.config import settings
from app.printkit.gateway import GatewayRejected, checkout_available
from app.printkit.stripe_gateway import StripeGateway


def test_checkout_stays_closed_without_the_secret_key(monkeypatch):
    monkeypatch.setattr(settings, "print_gateway", "stripe")
    monkeypatch.setattr(settings, "stripe_secret_key", "")
    assert checkout_available() is False


def test_create_charge_opens_a_brl_session(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_example")
    monkeypatch.setattr(settings, "public_web_origin", "https://storyrus.ai")
    captured: dict = {}

    def create(**kwargs):
        captured.update(kwargs)
        return {"id": "cs_test_123", "url": "https://checkout.stripe.com/c/pay/cs_test_123"}

    monkeypatch.setattr("stripe.checkout.Session.create", create)
    charge = StripeGateway().create_charge(order_code="SR1", amount_cents=18700, installments=1)
    assert charge.provider == "stripe"
    assert charge.reference == "cs_test_123"
    assert charge.checkout_url.startswith("https://checkout.stripe.com/")
    assert captured["line_items"][0]["price_data"]["currency"] == "brl"
    assert captured["line_items"][0]["price_data"]["unit_amount"] == 18700
    assert captured["success_url"] == "https://storyrus.ai/meus-pedidos?pagamento=ok"
    assert captured["metadata"]["order_code"] == "SR1"


def test_resume_returns_the_open_session(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_example")

    def retrieve(reference):
        assert reference == "cs_test_123"
        return {"id": reference, "status": "open", "payment_status": "unpaid", "url": "https://pay.test/open"}

    monkeypatch.setattr("stripe.checkout.Session.retrieve", retrieve)
    charge = StripeGateway().resume_charge("cs_test_123")
    assert charge is not None
    assert charge.checkout_url == "https://pay.test/open"


def test_resume_of_an_expired_session_is_empty(monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_example")
    monkeypatch.setattr(
        "stripe.checkout.Session.retrieve",
        lambda reference: {"id": reference, "status": "expired", "payment_status": "unpaid", "url": None},
    )
    assert StripeGateway().resume_charge("cs_test_old") is None


def test_webhook_accepts_a_paid_session(monkeypatch):
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test")

    def construct_event(body, signature, secret):
        assert signature == "sig"
        assert secret == "whsec_test"
        return json.loads(body)

    monkeypatch.setattr("stripe.Webhook.construct_event", construct_event)
    body = json.dumps(
        {
            "type": "checkout.session.completed",
            "data": {"object": {"id": "cs_test_123", "payment_status": "paid"}},
        }
    ).encode()
    notice = StripeGateway().parse_webhook(body, "sig")
    assert notice.paid is True
    assert notice.reference == "cs_test_123"
    assert notice.expired is False


def test_webhook_releases_an_expired_session(monkeypatch):
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test")
    monkeypatch.setattr(
        "stripe.Webhook.construct_event",
        lambda body, signature, secret: json.loads(body),
    )
    body = json.dumps(
        {
            "type": "checkout.session.expired",
            "data": {"object": {"id": "cs_test_123", "payment_status": "unpaid"}},
        }
    ).encode()
    notice = StripeGateway().parse_webhook(body, "sig")
    assert notice.paid is False
    assert notice.expired is True
    assert notice.reference == "cs_test_123"


def test_webhook_ignores_unrelated_events(monkeypatch):
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test")
    monkeypatch.setattr(
        "stripe.Webhook.construct_event",
        lambda body, signature, secret: json.loads(body),
    )
    body = json.dumps({"type": "charge.refunded", "data": {"object": {"id": "ch_1"}}}).encode()
    notice = StripeGateway().parse_webhook(body, "sig")
    assert notice.reference == ""
    assert notice.paid is False


def test_webhook_rejects_a_bad_signature(monkeypatch):
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test")

    def construct_event(body, signature, secret):
        raise ValueError("bad")

    monkeypatch.setattr("stripe.Webhook.construct_event", construct_event)
    with pytest.raises(GatewayRejected):
        StripeGateway().parse_webhook(b"{}", "nope")
