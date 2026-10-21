"""Pacote e validação do impresso. Mesma senha do painel de pedidos."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PrintOrder
from app.owner_auth import require_owner_password
from app.printkit.service import advance_validation, package_zip
from app.routers.projects.print import to_print_out
from app.schemas import PrintOrderOut, PrintValidationIn

router = APIRouter(prefix="/v1/print-orders", tags=["print"])


def _order(db: Session, order_id: uuid.UUID) -> PrintOrder:
    order = db.scalar(select(PrintOrder).where(PrintOrder.id == order_id))
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido de impressão não encontrado")
    return order


@router.get("/{order_id}/package", dependencies=[Depends(require_owner_password)])
def download_package(order_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    order = _order(db, order_id)
    if order.status not in {"files_ready", "sent_for_validation", "approved", "rejected"}:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            order.block_reason or "Arquivos de produção ainda não estão prontos.",
        )
    try:
        blob = package_zip(order)
    except FileNotFoundError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Arquivos de produção ainda não estão prontos.",
        ) from exc
    filename = f"{order.code}.zip"
    return Response(
        content=blob,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/{order_id}/validation",
    response_model=PrintOrderOut,
    dependencies=[Depends(require_owner_password)],
)
def set_validation(
    order_id: uuid.UUID,
    body: PrintValidationIn,
    db: Session = Depends(get_db),
) -> PrintOrderOut:
    order = _order(db, order_id)
    try:
        advance_validation(order, body.status)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Não dá para ir de {exc} para {body.status}.",
        ) from exc
    db.commit()
    db.refresh(order)
    return to_print_out(order)
