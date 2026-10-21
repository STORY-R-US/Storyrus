"""Pedido de livro impresso: arquivos, endereço, frete e pagamento."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_registered_user
from app.models import PrintOrder, Project, User
from app.printkit.gateway import GatewayNotConfigured, checkout_available
from app.printkit.service import (
    address_complete,
    apply_address,
    get_print_order,
    open_print_order,
    price_for,
    quote_order,
    select_freight,
    set_quantity,
    start_checkout,
)
from app.printkit.shipping import ShippingError, ShippingNotConfigured
from app.schemas import (
    FreightSelectIn,
    PrintAddressIn,
    PrintCheckoutIn,
    PrintOrderOut,
    PrintQuantityIn,
    ProjectOut,
)

from .common import get_owned_project

router = APIRouter()


def to_print_out(order: PrintOrder, *, checkout_url: str | None = None) -> PrintOrderOut:
    options = order.freight_options or []
    return PrintOrderOut(
        id=order.id,
        project_id=order.project_id,
        code=order.code,
        book_size=order.book_size,
        cover_type=order.cover_type,
        quantity=order.quantity,
        status=order.status,
        block_reason=order.block_reason,
        book_price_cents=price_for(order),
        freight_options=options,
        freight_service_id=order.freight_service_id,
        freight_service_name=order.freight_service_name,
        freight_price_cents=order.freight_price_cents,
        freight_days=order.freight_days,
        payment_status=order.payment_status,
        amount_cents=order.amount_cents,
        tracking_code=order.tracking_code,
        label_error=order.label_error,
        checkout_available=checkout_available(),
        checkout_url=checkout_url,
        recipient_name=order.recipient_name,
        postal_code=order.postal_code,
        street=order.street,
        number=order.number,
        complement=order.complement,
        district=order.district,
        city=order.city,
        state=order.state,
    )


def _owned_order(db: Session, user: User, project_id: uuid.UUID) -> tuple[Project, PrintOrder]:
    project = get_owned_project(db, user, project_id)
    order = get_print_order(db, project.id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido de impressão ainda não existe")
    return project, order


@router.post("/{project_id}/print-request", response_model=ProjectOut)
def request_print(
    project_id: uuid.UUID,
    user: User = Depends(require_registered_user),
    db: Session = Depends(get_db),
) -> Project:
    """Abre o pedido impresso. Sem spec completa, não publica arquivo de produção."""
    project = get_owned_project(db, user, project_id)
    if not project.book_approved_at:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Aprove o livro antes de pedir o impresso")
    if not project.ebook_url:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "E-book ausente")
    open_print_order(db, project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}/print-order", response_model=PrintOrderOut)
def read_print_order(
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PrintOrderOut:
    _project, order = _owned_order(db, user, project_id)
    return to_print_out(order)


@router.put("/{project_id}/print-order/address", response_model=PrintOrderOut)
def save_print_address(
    project_id: uuid.UUID,
    body: PrintAddressIn,
    user: User = Depends(require_registered_user),
    db: Session = Depends(get_db),
) -> PrintOrderOut:
    _project, order = _owned_order(db, user, project_id)
    apply_address(order, body.model_dump())
    if not address_complete(order):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Endereço de entrega incompleto.")
    db.commit()
    db.refresh(order)
    return to_print_out(order)


@router.put("/{project_id}/print-order/quantity", response_model=PrintOrderOut)
def save_print_quantity(
    project_id: uuid.UUID,
    body: PrintQuantityIn,
    user: User = Depends(require_registered_user),
    db: Session = Depends(get_db),
) -> PrintOrderOut:
    _project, order = _owned_order(db, user, project_id)
    try:
        set_quantity(order, body.quantity)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    db.commit()
    db.refresh(order)
    return to_print_out(order)


@router.post("/{project_id}/print-order/freight", response_model=PrintOrderOut)
def quote_print_freight(
    project_id: uuid.UUID,
    user: User = Depends(require_registered_user),
    db: Session = Depends(get_db),
) -> PrintOrderOut:
    _project, order = _owned_order(db, user, project_id)
    try:
        options = quote_order(order)
    except ShippingNotConfigured as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Frete ainda não configurado: " + ", ".join(exc.gaps),
        ) from exc
    except ShippingError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    if not options:
        raise HTTPException(status.HTTP_409_CONFLICT, "Nenhuma opção de frete disponível.")
    db.commit()
    db.refresh(order)
    return to_print_out(order)


@router.post("/{project_id}/print-order/freight/select", response_model=PrintOrderOut)
def choose_print_freight(
    project_id: uuid.UUID,
    body: FreightSelectIn,
    user: User = Depends(require_registered_user),
    db: Session = Depends(get_db),
) -> PrintOrderOut:
    _project, order = _owned_order(db, user, project_id)
    try:
        select_freight(order, body.service_id)
    except ShippingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    db.commit()
    db.refresh(order)
    return to_print_out(order)


@router.post("/{project_id}/print-order/checkout", response_model=PrintOrderOut)
def checkout_print(
    project_id: uuid.UUID,
    body: PrintCheckoutIn,
    user: User = Depends(require_registered_user),
    db: Session = Depends(get_db),
) -> PrintOrderOut:
    _project, order = _owned_order(db, user, project_id)
    try:
        charge = start_checkout(order, body.installments)
    except GatewayNotConfigured as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Gateway de pagamento ainda não escolhido.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    db.commit()
    db.refresh(order)
    return to_print_out(order, checkout_url=charge.checkout_url)
