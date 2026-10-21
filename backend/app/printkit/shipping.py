"""Cotação e etiqueta no Melhor Envio. Sem token, sem prazo inventado."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

import httpx

from app.config import settings


class ShippingNotConfigured(Exception):
    def __init__(self, gaps: list[str]):
        self.gaps = gaps
        super().__init__(", ".join(gaps))


class ShippingError(Exception):
    pass


@dataclass(frozen=True)
class FreightOption:
    service_id: int
    service_name: str
    price_cents: int
    delivery_days: int | None

    def as_dict(self) -> dict:
        return {
            "service_id": self.service_id,
            "service_name": self.service_name,
            "price_cents": self.price_cents,
            "delivery_days": self.delivery_days,
        }


@dataclass(frozen=True)
class LabelResult:
    tracking: str | None
    url: str | None
    error: str | None = None


def _digits(value: str | None) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def quote_gaps() -> list[str]:
    gaps: list[str] = []
    if not (settings.melhor_envio_token or "").strip():
        gaps.append("melhor_envio_token")
    if len(_digits(settings.melhor_envio_from_postal_code)) != 8:
        gaps.append("melhor_envio_from_postal_code")
    if settings.print_package_weight_g is None:
        gaps.append("package_weight_g")
    if settings.print_package_height_cm is None:
        gaps.append("package_height_cm")
    if settings.print_package_width_cm is None:
        gaps.append("package_width_cm")
    if settings.print_package_length_cm is None:
        gaps.append("package_length_cm")
    return gaps


def label_gaps() -> list[str]:
    gaps = quote_gaps()
    for name, value in (
        ("melhor_envio_from_name", settings.melhor_envio_from_name),
        ("melhor_envio_from_address", settings.melhor_envio_from_address),
        ("melhor_envio_from_number", settings.melhor_envio_from_number),
        ("melhor_envio_from_city", settings.melhor_envio_from_city),
        ("melhor_envio_from_state", settings.melhor_envio_from_state),
    ):
        if not (value or "").strip():
            gaps.append(name)
    return gaps


def _base() -> str:
    if settings.melhor_envio_sandbox:
        return "https://sandbox.melhorenvio.com.br"
    return "https://melhorenvio.com.br"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.melhor_envio_token.strip()}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": settings.melhor_envio_user_agent,
    }


def _post(url: str, payload: dict) -> httpx.Response:
    with httpx.Client(timeout=30) as client:
        return client.post(url, headers=_headers(), json=payload)


def _cents(raw) -> int | None:
    if raw is None or raw == "":
        return None
    try:
        value = Decimal(str(raw))
    except Exception:
        return None
    return int((value * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _days(raw) -> int | None:
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _package() -> dict:
    weight_g = int(settings.print_package_weight_g or 0)
    return {
        "height": float(settings.print_package_height_cm or 0),
        "width": float(settings.print_package_width_cm or 0),
        "length": float(settings.print_package_length_cm or 0),
        "weight": weight_g / 1000.0,
    }


def quote_freight(to_postal_code: str) -> list[FreightOption]:
    gaps = quote_gaps()
    if gaps:
        raise ShippingNotConfigured(gaps)
    to_code = _digits(to_postal_code)
    if len(to_code) != 8:
        raise ShippingError("CEP de entrega inválido.")
    response = _post(
        f"{_base()}/api/v2/me/shipment/calculate",
        {
            "from": {"postal_code": _digits(settings.melhor_envio_from_postal_code)},
            "to": {"postal_code": to_code},
            "package": _package(),
        },
    )
    if response.status_code >= 400:
        raise ShippingError(f"Melhor Envio recusou a cotação ({response.status_code}).")
    body = response.json()
    if not isinstance(body, list):
        raise ShippingError("Resposta de cotação inesperada.")
    options: list[FreightOption] = []
    for item in body:
        if not isinstance(item, dict) or item.get("error"):
            continue
        quoted = item.get("custom_price")
        if quoted in (None, ""):
            quoted = item.get("price")
        price = _cents(quoted)
        service_id = item.get("id")
        name = (item.get("name") or "").strip()
        if price is None or service_id is None or not name:
            continue
        options.append(
            FreightOption(
                service_id=int(service_id),
                service_name=name,
                price_cents=price,
                delivery_days=_days(item.get("delivery_time")),
            )
        )
    return options


def buy_label(order) -> LabelResult:
    gaps = label_gaps()
    if gaps:
        raise ShippingNotConfigured(gaps)
    if order.freight_service_id is None:
        raise ShippingError("Nenhum frete selecionado.")
    to_code = _digits(order.postal_code)
    if len(to_code) != 8:
        raise ShippingError("CEP de entrega inválido.")
    payload = {
        "service": order.freight_service_id,
        "from": {
            "name": settings.melhor_envio_from_name.strip(),
            "postal_code": _digits(settings.melhor_envio_from_postal_code),
            "address": settings.melhor_envio_from_address.strip(),
            "number": settings.melhor_envio_from_number.strip(),
            "district": (settings.melhor_envio_from_district or "").strip(),
            "city": settings.melhor_envio_from_city.strip(),
            "state_abbr": settings.melhor_envio_from_state.strip(),
        },
        "to": {
            "name": order.recipient_name or "",
            "postal_code": to_code,
            "address": order.street or "",
            "number": order.number or "",
            "complement": order.complement or "",
            "district": order.district or "",
            "city": order.city or "",
            "state_abbr": order.state or "",
        },
        "products": [
            {
                "name": f"Livro {order.code}",
                "quantity": order.quantity or 1,
                "unitary_value": (order.amount_cents or 0) / 100.0,
            }
        ],
        "volumes": [_package()],
    }
    cart = _post(f"{_base()}/api/v2/me/cart", payload)
    if cart.status_code >= 400:
        raise ShippingError(f"Melhor Envio recusou o carrinho ({cart.status_code}).")
    cart_body = cart.json()
    order_id = cart_body.get("id") if isinstance(cart_body, dict) else None
    if not order_id:
        raise ShippingError("Melhor Envio não devolveu o pedido da etiqueta.")
    checkout = _post(f"{_base()}/api/v2/me/shipment/checkout", {"orders": [order_id]})
    if checkout.status_code >= 400:
        raise ShippingError(
            f"Melhor Envio recusou o pagamento da etiqueta ({checkout.status_code})."
        )
    generated = _post(f"{_base()}/api/v2/me/shipment/generate", {"orders": [order_id]})
    if generated.status_code >= 400:
        raise ShippingError(f"Melhor Envio não gerou a etiqueta ({generated.status_code}).")
    tracking = _post(f"{_base()}/api/v2/me/shipment/tracking", {"orders": [order_id]})
    if tracking.status_code >= 400:
        return LabelResult(tracking=None, url=None, error="Rastreio ainda não disponível.")
    data = tracking.json()
    row = data.get(str(order_id)) if isinstance(data, dict) else None
    if not isinstance(row, dict):
        row = next(iter(data.values()), None) if isinstance(data, dict) and data else None
    if not isinstance(row, dict):
        return LabelResult(tracking=None, url=None, error="A transportadora não devolveu rastreio.")
    code = row.get("tracking") or row.get("melhorenvio_tracking") or None
    url = row.get("tracking_url") or None
    if code is not None:
        code = str(code).strip() or None
    return LabelResult(tracking=code, url=url if isinstance(url, str) else None)
