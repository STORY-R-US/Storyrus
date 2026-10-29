"""Stripe Checkout do livro impresso. As chaves ficam só no ambiente."""

from __future__ import annotations

import logging

import stripe

from app.config import settings
from app.printkit.gateway import (
    ChargeResult,
    GatewayNotConfigured,
    GatewayRejected,
    PaymentNotice,
    register_gateway,
)

log = logging.getLogger(__name__)

_PAID_EVENTS = frozenset(
    {
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
    }
)


def _field(obj: object, name: str):
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


class StripeGateway:
    name = "stripe"

    def ready(self) -> bool:
        return bool((settings.stripe_secret_key or "").strip())

    def _use_key(self) -> None:
        key = (settings.stripe_secret_key or "").strip()
        if not key:
            raise GatewayNotConfigured()
        stripe.api_key = key

    def create_charge(
        self,
        *,
        order_code: str,
        amount_cents: int,
        installments: int,
    ) -> ChargeResult:
        self._use_key()
        if amount_cents <= 0:
            raise ValueError("Valor do pedido ausente.")
        origin = (settings.public_web_origin or "https://storyrus.ai").rstrip("/")
        try:
            session = stripe.checkout.Session.create(
                mode="payment",
                client_reference_id=order_code,
                metadata={"order_code": order_code, "installments": str(installments)},
                line_items=[
                    {
                        "quantity": 1,
                        "price_data": {
                            "currency": "brl",
                            "unit_amount": amount_cents,
                            "product_data": {"name": f"Livro personalizado {order_code}"},
                        },
                    }
                ],
                success_url=f"{origin}/meus-pedidos?pagamento=ok",
                cancel_url=f"{origin}/meus-pedidos?pagamento=cancelado",
            )
        except Exception as exc:
            log.warning("stripe checkout failed: %s", type(exc).__name__)
            raise ValueError("O Stripe não abriu o pagamento. Tente de novo.") from exc
        session_id = str(_field(session, "id") or "")
        url = str(_field(session, "url") or "")
        if not session_id or not url:
            raise ValueError("O Stripe não abriu o pagamento. Tente de novo.")
        if len(session_id) > 80:
            log.error("stripe session id is longer than payment_reference")
            raise ValueError("O Stripe não abriu o pagamento. Tente de novo.")
        return ChargeResult(provider=self.name, reference=session_id, checkout_url=url)

    def resume_charge(self, reference: str) -> ChargeResult | None:
        self._use_key()
        if not reference:
            return None
        try:
            session = stripe.checkout.Session.retrieve(reference)
        except Exception as exc:
            log.warning("stripe session retrieve failed: %s", type(exc).__name__)
            return None
        if _field(session, "payment_status") == "paid":
            raise ValueError("Este pedido já está pago.")
        url = _field(session, "url")
        if _field(session, "status") == "open" and url:
            return ChargeResult(
                provider=self.name,
                reference=str(_field(session, "id") or reference),
                checkout_url=str(url),
            )
        return None

    def parse_webhook(self, body: bytes, signature: str | None) -> PaymentNotice:
        secret = (settings.stripe_webhook_secret or "").strip()
        if not secret or not signature:
            raise GatewayRejected("Assinatura ausente")
        try:
            event = stripe.Webhook.construct_event(body, signature, secret)
        except Exception as exc:
            if exc.__class__.__name__ not in {"SignatureVerificationError", "ValueError"}:
                raise
            raise GatewayRejected("Assinatura inválida") from exc
        event_type = _field(event, "type")
        data_obj = _field(event, "data")
        session = _field(data_obj, "object")
        reference = str(_field(session, "id") or "")
        if event_type == "checkout.session.expired":
            return PaymentNotice(reference=reference, paid=False, expired=True)
        if event_type not in _PAID_EVENTS:
            return PaymentNotice(reference="", paid=False)
        return PaymentNotice(
            reference=reference,
            paid=_field(session, "payment_status") == "paid",
        )


register_gateway(StripeGateway())
