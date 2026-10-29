"""Encaixe do gateway. O provedor ativo vem de PRINT_GATEWAY."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.config import settings


class GatewayNotConfigured(Exception):
    pass


class GatewayRejected(Exception):
    pass


@dataclass(frozen=True)
class ChargeResult:
    provider: str
    reference: str
    checkout_url: str | None


@dataclass(frozen=True)
class PaymentNotice:
    reference: str
    paid: bool
    expired: bool = False


class PrintGateway(Protocol):
    name: str

    def create_charge(
        self,
        *,
        order_code: str,
        amount_cents: int,
        installments: int,
    ) -> ChargeResult: ...

    def parse_webhook(self, body: bytes, signature: str | None) -> PaymentNotice: ...


_REGISTRY: dict[str, PrintGateway] = {}


def register_gateway(gateway: PrintGateway) -> None:
    _REGISTRY[gateway.name] = gateway


def unregister_gateway(name: str) -> None:
    _REGISTRY.pop(name, None)


def checkout_available() -> bool:
    name = (settings.print_gateway or "").strip()
    gateway = _REGISTRY.get(name)
    if gateway is None:
        return False
    ready = getattr(gateway, "ready", None)
    if callable(ready):
        return bool(ready())
    return True


def configured_gateway() -> PrintGateway:
    name = (settings.print_gateway or "").strip()
    gateway = _REGISTRY.get(name)
    if not name or gateway is None:
        raise GatewayNotConfigured()
    return gateway
