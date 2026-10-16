"""Pedido impresso: arquivos, pacote, endereço, frete e pagamento."""

from __future__ import annotations

import io
import json
import uuid
import zipfile

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import storage
from app.config import settings
from app.models import Asset, AssetKind, PrintOrder, Project, _now
from app.printkit.files import build_print_pdfs
from app.printkit.gateway import configured_gateway
from app.printkit.pricing import book_price_cents
from app.printkit.shipping import ShippingError, ShippingNotConfigured, buy_label
from app.printkit.spec import PrintPagesMissing, PrintSpecIncomplete, spec_from_settings

_FILE_STATUSES = frozenset({"files_ready", "sent_for_validation", "approved", "rejected"})
_FORWARD = {
    "files_ready": frozenset({"sent_for_validation"}),
    "sent_for_validation": frozenset({"approved", "rejected"}),
}


def order_code(order_id: uuid.UUID) -> str:
    return "SR-" + order_id.hex[:8].upper()


def get_print_order(db: Session, project_id: uuid.UUID) -> PrintOrder | None:
    return db.scalar(select(PrintOrder).where(PrintOrder.project_id == project_id))


def invalidate_print(db: Session, project: Project) -> None:
    """Livro refeito: o pacote antigo deixa de valer, salvo se o impresso já foi pago."""
    order = get_print_order(db, project.id)
    if order is None or order.payment_status != "paid":
        project.print_requested_at = None
        project.print_status = None
    if order is None or order.payment_status == "paid":
        return
    order.cover_key = None
    order.interior_key = None
    order.status = "awaiting_spec"
    order.block_reason = None
    order.freight_options = None
    order.freight_service_id = None
    order.freight_service_name = None
    order.freight_price_cents = None
    order.freight_days = None
    order.payment_status = "unpaid"
    order.payment_provider = None
    order.payment_reference = None
    order.amount_cents = None
    order.label_error = None


def _sync(project: Project, order: PrintOrder) -> None:
    project.print_status = order.status


def _page_images(db: Session, project: Project) -> list[bytes]:
    rows = db.scalars(
        select(Asset)
        .where(Asset.project_id == project.id, Asset.kind == AssetKind.PAGE_IMAGE.value)
        .order_by(Asset.created_at.asc())
    ).all()
    if (project.book_profile or {}).get("version") == 1:
        rows = [
            row
            for row in rows
            if (row.meta or {}).get("workflow") == 1
            and (row.meta or {}).get("role") == "com_texto"
            and (row.meta or {}).get("language") == project.language
        ]
        if len(rows) != 16:
            return []
    ordered = sorted(rows, key=lambda row: int((row.meta or {}).get("page") or 0))
    images: list[bytes] = []
    for row in ordered:
        try:
            images.append(storage.get_bytes(row.storage_key))
        except Exception:
            continue
    return images


def _store_pdf(project_id: uuid.UUID, kind: str, blob: bytes) -> str:
    key = storage.new_key(project_id, kind, "pdf")
    storage.put_bytes(key, blob, "application/pdf")
    return key


def prepare_files(db: Session, project: Project, order: PrintOrder) -> None:
    """Gera capa e miolo só com a spec completa. Caso contrário não publica arquivo."""
    if order.status in {"sent_for_validation", "approved"} or order.payment_status == "paid":
        return
    order.book_size = project.book_size
    order.cover_type = project.cover_type
    if order.quantity < 1:
        order.quantity = 1
    if order.book_size not in {"P", "M"} or order.cover_type not in {"soft", "hard"}:
        order.status = "awaiting_spec"
        order.block_reason = "Tamanho ou tipo de capa ausente no projeto."
        order.cover_key = None
        order.interior_key = None
        _sync(project, order)
        return
    if (
        order.book_size == "P"
        and order.cover_type == "hard"
        and not settings.print_allow_p_hardcover
    ):
        order.status = "held"
        order.block_reason = "15 × 15 cm em capa dura ainda não foi liberado pela produção."
        order.cover_key = None
        order.interior_key = None
        _sync(project, order)
        return
    spec = spec_from_settings()
    gaps = spec.missing(order.cover_type)
    if gaps:
        order.status = "awaiting_spec"
        order.block_reason = "Especificação de produção incompleta: " + ", ".join(gaps)
        order.cover_key = None
        order.interior_key = None
        _sync(project, order)
        return
    pages = _page_images(db, project)
    if not pages:
        order.status = "awaiting_pages"
        order.block_reason = "O livro ainda não tem páginas ilustradas para o miolo."
        order.cover_key = None
        order.interior_key = None
        _sync(project, order)
        return
    try:
        cover_pdf, interior_pdf = build_print_pdfs(
            order_code=order.code,
            book_size=order.book_size,
            cover_type=order.cover_type,
            spec=spec,
            interior_pages=pages,
            front_cover=_approved_cover(db, project),
        )
    except PrintPagesMissing:
        order.status = "awaiting_pages"
        order.block_reason = "O livro ainda não tem páginas ilustradas para o miolo."
        order.cover_key = None
        order.interior_key = None
        _sync(project, order)
        return
    except PrintSpecIncomplete as exc:
        order.status = "awaiting_spec"
        order.block_reason = str(exc)
        order.cover_key = None
        order.interior_key = None
        _sync(project, order)
        return
    order.cover_key = _store_pdf(project.id, "print_cover", cover_pdf)
    order.interior_key = _store_pdf(project.id, "print_interior", interior_pdf)
    order.status = "files_ready"
    order.block_reason = None
    _sync(project, order)


def _approved_cover(db: Session, project: Project) -> bytes | None:
    if not (project.book_profile or {}).get("version") == 1:
        return None
    rows = db.scalars(
        select(Asset).where(Asset.project_id == project.id, Asset.kind == AssetKind.COVER.value)
    ).all()
    for row in rows:
        if (row.meta or {}).get("language") == project.language:
            return storage.get_bytes(row.storage_key)
    return None


def _seed_delivery(order: PrintOrder, project: Project) -> None:
    """Copia o cadastro da conta para a OS quando o endereço ainda está vazio."""
    if (order.recipient_name or "").strip():
        return
    user = project.user
    if user is None:
        return
    name = (user.full_name or "").strip() or (user.email or "").strip()
    if name:
        order.recipient_name = name[:120]
    postal = "".join(ch for ch in (user.postal_code or "") if ch.isdigit())
    if len(postal) == 8:
        order.postal_code = postal
    if (user.street or "").strip():
        order.street = user.street.strip()[:160]
    if (user.number or "").strip():
        order.number = user.number.strip()[:20]
    if (user.complement or "").strip():
        order.complement = user.complement.strip()[:80]
    if (user.district or "").strip():
        order.district = user.district.strip()[:80]
    if (user.city or "").strip():
        order.city = user.city.strip()[:80]
    state = (user.state or "").strip().upper()
    if len(state) == 2:
        order.state = state


def open_print_order(
    db: Session,
    project: Project,
    *,
    requested: bool = True,
    prepare: bool = True,
) -> PrintOrder:
    """Abre a OS do livro. `requested` marca o impresso pedido pela família.

    `prepare` gera os PDFs. A listagem do painel passa False: senão cada
    página vira uma leitura no storage e o Pedidos fica em "Abrindo…".
    """
    order = get_print_order(db, project.id)
    if order is None:
        order_id = uuid.uuid4()
        order = PrintOrder(
            id=order_id,
            project_id=project.id,
            code=order_code(order_id),
            quantity=1,
            status="awaiting_spec",
            payment_status="unpaid",
        )
        db.add(order)
        db.flush()
    if requested and project.print_requested_at is None:
        project.print_requested_at = _now()
    _seed_delivery(order, project)
    if prepare:
        prepare_files(db, project, order)
    _sync(project, order)
    return order


def attach_service_orders(
    db: Session,
    projects: list[Project],
    *,
    prepare: bool = True,
) -> None:
    """Garante uma OS por pedido. `prepare` monta o PDF quando as páginas chegam."""
    changed = False
    for project in projects:
        order = get_print_order(db, project.id)
        if order is None:
            open_print_order(db, project, requested=False, prepare=prepare)
            changed = True
            continue
        if prepare and order.status == "awaiting_pages":
            prepare_files(db, project, order)
            changed = True
    if changed:
        db.commit()


def package_zip(order: PrintOrder) -> bytes:
    if not order.cover_key or not order.interior_key:
        raise FileNotFoundError(order.code)
    spec = spec_from_settings()
    cover_name = spec.file_name(order.code, "capa")
    interior_name = spec.file_name(order.code, "miolo")
    manifest = {
        "code": order.code,
        "book_size": order.book_size,
        "cover_type": order.cover_type,
        "quantity": order.quantity,
        "files": {"capa": cover_name, "miolo": interior_name},
        "pdf_x": spec.pdf_x,
        "color_profile": spec.color_profile,
        "production_ready": order.status in _FILE_STATUSES,
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(cover_name, storage.get_bytes(order.cover_key))
        archive.writestr(interior_name, storage.get_bytes(order.interior_key))
        archive.writestr(
            "pedido.json",
            json.dumps(manifest, ensure_ascii=False).encode("utf-8"),
        )
    return buf.getvalue()


def advance_validation(order: PrintOrder, target: str) -> None:
    allowed = _FORWARD.get(order.status, frozenset())
    if target not in allowed:
        raise ValueError(order.status)
    order.status = target
    if order.project is not None:
        _sync(order.project, order)


def address_complete(order: PrintOrder) -> bool:
    postal = "".join(ch for ch in (order.postal_code or "") if ch.isdigit())
    return bool(
        (order.recipient_name or "").strip()
        and len(postal) == 8
        and (order.street or "").strip()
        and (order.number or "").strip()
        and (order.district or "").strip()
        and (order.city or "").strip()
        and len((order.state or "").strip()) == 2
    )


def set_quantity(order: PrintOrder, quantity: int) -> None:
    if order.payment_status in {"paid", "pending"}:
        raise ValueError("A quantidade não pode mudar depois do pagamento.")
    order.quantity = quantity


def apply_address(order: PrintOrder, data: dict) -> None:
    order.recipient_name = data["recipient_name"].strip()
    order.postal_code = "".join(ch for ch in data["postal_code"] if ch.isdigit())
    order.street = data["street"].strip()
    order.number = data["number"].strip()
    order.complement = (data.get("complement") or "").strip() or None
    order.district = data["district"].strip()
    order.city = data["city"].strip()
    order.state = data["state"].strip().upper()


def quote_order(order: PrintOrder):
    from app.printkit.shipping import quote_freight

    if not address_complete(order):
        raise ShippingError("Endereço de entrega incompleto.")
    options = quote_freight(order.postal_code or "")
    order.freight_options = [item.as_dict() for item in options]
    order.freight_service_id = None
    order.freight_service_name = None
    order.freight_price_cents = None
    order.freight_days = None
    return options


def select_freight(order: PrintOrder, service_id: int) -> None:
    match = next(
        (item for item in (order.freight_options or []) if item.get("service_id") == service_id),
        None,
    )
    if match is None:
        raise ShippingError("Opção de frete não encontrada. Calcule de novo.")
    order.freight_service_id = int(match["service_id"])
    order.freight_service_name = match.get("service_name")
    order.freight_price_cents = int(match["price_cents"])
    days = match.get("delivery_days")
    order.freight_days = int(days) if days is not None else None


def start_checkout(order: PrintOrder, installments: int):
    if order.book_size not in {"P", "M"}:
        raise ValueError("Tamanho do livro ausente.")
    if order.status == "held":
        raise ValueError(order.block_reason or "Formato ainda não liberado.")
    if order.status not in _FILE_STATUSES:
        raise ValueError("Os arquivos de produção ainda não estão prontos.")
    if not address_complete(order):
        raise ValueError("Endereço de entrega incompleto.")
    if order.freight_price_cents is None or order.freight_service_id is None:
        raise ValueError("Selecione o frete antes de pagar.")
    gateway = configured_gateway()
    copies = max(1, int(order.quantity or 1))
    book = book_price_cents(order.book_size) * copies
    amount = book + int(order.freight_price_cents)
    charge = gateway.create_charge(
        order_code=order.code,
        amount_cents=amount,
        installments=installments,
    )
    order.payment_status = "pending"
    order.payment_provider = charge.provider
    order.payment_reference = charge.reference
    order.amount_cents = amount
    return charge


def fulfill_payment(db: Session, order: PrintOrder) -> None:
    if order.payment_status != "paid":
        order.payment_status = "paid"
    if order.tracking_code:
        return
    try:
        result = buy_label(order)
    except ShippingNotConfigured as exc:
        order.label_error = "Etiqueta não comprada: " + ", ".join(exc.gaps)
        return
    except ShippingError as exc:
        order.label_error = str(exc)
        return
    order.tracking_code = result.tracking
    order.label_url = result.url
    if result.tracking:
        order.label_error = None
    else:
        order.label_error = result.error or "A transportadora não devolveu código de rastreio."
    db.add(order)


def price_for(order: PrintOrder) -> int | None:
    try:
        return book_price_cents(order.book_size)
    except ValueError:
        return None
