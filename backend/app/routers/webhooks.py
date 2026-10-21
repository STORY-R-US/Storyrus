"""Callbacks dos provedores lentos (video/3D).

O worker registra o job como RUNNING e libera a thread; o provedor chama de
volta aqui quando termina. A assinatura HMAC (timestamp + nonce) valida a
autenticidade e bloqueia replay.
"""

import json
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Asset, AssetKind, Job, JobStatus, PrintOrder, Project, ProjectStatus
from app.printkit.gateway import GatewayNotConfigured, GatewayRejected, configured_gateway
from app.printkit.service import fulfill_payment
from app.services import webhook_auth

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])


@router.post("/video", status_code=status.HTTP_200_OK)
async def video_callback(
    request: Request,
    x_signature: str | None = Header(default=None, alias="X-Signature"),
    x_timestamp: str | None = Header(default=None, alias="X-Timestamp"),
    x_nonce: str | None = Header(default=None, alias="X-Nonce"),
    db: Session = Depends(get_db),
) -> dict:
    raw = await request.body()
    err = webhook_auth.verify_signature(
        secret=settings.webhook_signing_secret,
        body=raw,
        signature=x_signature,
        timestamp=x_timestamp,
        nonce=x_nonce,
    )
    if err:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, err)

    body = json.loads(raw or b"{}")
    job_id = body.get("job_id")
    if not job_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "job_id ausente")

    job = db.get(Job, uuid.UUID(job_id))
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job nao encontrado")

    # Idempotente: callback repetido nao reprocessa.
    if job.status == JobStatus.DONE.value:
        return {"ok": True, "idempotent": True}

    project = db.get(Project, job.project_id)
    if body.get("status") == "success":
        storage_key = body.get("storage_key") or body.get("video_url", "")
        job.status = JobStatus.DONE.value
        job.result = {"video": storage_key}
        if project is not None:
            project.video_url = storage_key
            project.status = ProjectStatus.VIDEO_READY.value
            db.add(
                Asset(project_id=project.id, kind=AssetKind.VIDEO.value, storage_key=storage_key)
            )
    else:
        from app.services import jobs as jobs_svc

        jobs_svc.mark_failed_and_refund(db, job, body.get("error", "callback failed"))
        return {"ok": True}

    db.commit()
    return {"ok": True}


@router.post("/print-payment", status_code=status.HTTP_200_OK)
async def print_payment_callback(
    request: Request,
    x_print_signature: str | None = Header(default=None, alias="X-Print-Signature"),
    db: Session = Depends(get_db),
) -> dict:
    """Confirma o pagamento e só então compra a etiqueta."""
    raw = await request.body()
    try:
        gateway = configured_gateway()
    except GatewayNotConfigured as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Gateway de pagamento ainda não escolhido.",
        ) from exc
    try:
        notice = gateway.parse_webhook(raw, x_print_signature)
    except GatewayRejected as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    order = db.scalar(select(PrintOrder).where(PrintOrder.payment_reference == notice.reference))
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido de impressão não encontrado")
    if notice.paid:
        fulfill_payment(db, order)
    db.commit()
    return {"ok": True, "paid": notice.paid}
