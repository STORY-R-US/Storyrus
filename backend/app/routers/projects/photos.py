"""Upload de fotos e personagens extras."""

from __future__ import annotations

import logging
import uuid
from io import BytesIO

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from PIL import Image
from sqlalchemy.orm import Session

from app import storage
from app.config import settings
from app.database import get_db
from app.deps import require_adult_user
from app.models import Asset, AssetKind, OrderTicket, Project, User
from app.order_tickets import register_order_ticket, resolve_buyer
from app.schemas import UploadUrlIn, UploadUrlOut
from app.services.transactional_email import send_new_order_email

from .common import get_owned_project

router = APIRouter()
logger = logging.getLogger(__name__)

# Lado maior guardado. Acima disso o GPT Image estoura o tempo da prévia.
_MAX_EDGE = 2048


def _normalize_photo(data: bytes) -> bytes:
    """JPEG que o Pillow (e o provedor de imagem) conseguem abrir.

    HEIC do iPhone e arquivo que não é imagem viram 400 aqui, em vez de
    um projeto CREATED cujo avatar falha minutos depois no worker.
    """
    try:
        image = Image.open(BytesIO(data))
        image.load()
    except Exception as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Não foi possível ler a foto. Envie JPG, PNG ou WEBP. "
            "No iPhone, exporte a foto HEIC nesses formatos.",
        ) from exc
    image = image.convert("RGB")
    width, height = image.size
    edge = max(width, height)
    if edge > _MAX_EDGE:
        scale = _MAX_EDGE / float(edge)
        image = image.resize(
            (max(1, int(width * scale)), max(1, int(height * scale))),
            Image.Resampling.LANCZOS,
        )
    buf = BytesIO()
    image.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _schedule_new_order_notice(
    background: BackgroundTasks,
    project: Project,
    ticket: OrderTicket,
    user: User,
) -> None:
    """Agenda o aviso interno — monta os dados aqui (sessão aberta) e envia depois."""
    background.add_task(
        send_new_order_email,
        child_name=(project.child_name or "").strip(),
        summary=ticket.summary or "",
        client_name=(user.full_name or "").strip(),
        client_email=(user.email or "").strip(),
    )


def _save_photo_asset(db: Session, project: Project, key: str) -> Asset:
    """Grava o asset da foto e confirma — sem depender do pedido/impresso.

    A foto é o insumo que a geração precisa; o pedido do dono é recuperável
    depois por `backfill_order_tickets`. Separar as duas coisas evita que uma
    falha de bookkeeping (pedido, impresso, e-mail) derrube o upload com 500.
    """
    asset = Asset(project_id=project.id, kind=AssetKind.PHOTO.value, storage_key=key)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def _register_order_bookkeeping(
    db: Session, project: Project, **kwargs: str
) -> tuple[OrderTicket | None, bool]:
    """Abre/atualiza o pedido sem nunca propagar erro para o clique.

    Retorna `(ticket, created)`. Em falha, desfaz só o pedido e devolve
    `(None, False)`; a foto já está salva e a geração continua.
    """
    try:
        ticket, created = register_order_ticket(db, project, **kwargs)
        db.commit()
        return ticket, created
    except Exception:  # noqa: BLE001 - bookkeeping não pode virar 500 na foto
        logger.exception("pedido da foto falhou project=%s", project.id)
        db.rollback()
        return None, False


@router.post("/{project_id}/photos", response_model=UploadUrlOut, status_code=201)
def request_photo_upload(
    project_id: uuid.UUID,
    body: UploadUrlIn,
    background: BackgroundTasks,
    user: User = Depends(require_adult_user),
    db: Session = Depends(get_db),
) -> UploadUrlOut:
    """Gera URL assinada de upload e registra o asset (foto de origem)."""
    project = get_owned_project(db, user, project_id)
    key = storage.new_key(project.id, AssetKind.PHOTO.value, body.ext)
    try:
        buyer = resolve_buyer(user)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    asset = _save_photo_asset(db, project, key)
    asset_id = asset.id
    ticket, created = _register_order_bookkeeping(
        db,
        project,
        language=project.language or "pt-BR",
        theme_label=project.theme or "",
        client_name=buyer["name"],
        client_email=buyer["email"],
        client_phone=buyer["phone"],
        client_address=buyer["address"],
        client_notes=buyer["notes"],
    )
    if created and ticket is not None:
        _schedule_new_order_notice(background, project, ticket, user)
    return UploadUrlOut(
        asset_id=asset_id,
        storage_key=key,
        upload_url=storage.presign_put(key, body.content_type),
        expires_in=settings.storage_signing_ttl,
    )


@router.post("/{project_id}/photo", response_model=UploadUrlOut, status_code=201)
async def upload_photo(
    project_id: uuid.UUID,
    background: BackgroundTasks,
    user: User = Depends(require_adult_user),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    language: str = Form(""),
    theme_label: str = Form(""),
    extra_names: str = Form(""),
    gender: str = Form(""),
    subject: str = Form(""),
    also_name: str = Form(""),
    also_gender: str = Form(""),
    also_subject: str = Form(""),
    quantity: str = Form(""),
    client_name: str = Form(""),
    client_email: str = Form(""),
    client_phone: str = Form(""),
    client_address: str = Form(""),
    client_notes: str = Form(""),
    finalize: str = Form("1"),
) -> UploadUrlOut:
    """Upload da foto via API: o servidor grava direto no storage (sem PUT do navegador).

    Com a foto gravada, abre (ou atualiza) o pedido que o dono lê em /pedidos.
    `finalize` fica só para o cliente saber quando a leva terminou — o ticket já
    abre na primeira foto.
    """
    del finalize  # aceito no form por compatibilidade com o Studio
    project = get_owned_project(db, user, project_id)
    data = await file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Arquivo vazio")
    if len(data) > 10_000_000:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Imagem muito grande (max. 10MB)"
        )
    data = _normalize_photo(data)
    try:
        buyer = resolve_buyer(
            user,
            client_name=client_name,
            client_email=client_email,
            client_phone=client_phone,
            client_address=client_address,
            client_notes=client_notes,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    key = storage.new_key(project.id, AssetKind.PHOTO.value, "jpg")
    storage.put_bytes(key, data, "image/jpeg")
    asset = _save_photo_asset(db, project, key)
    asset_id = asset.id
    ticket, created = _register_order_bookkeeping(
        db,
        project,
        language=language,
        theme_label=theme_label,
        extra_names=extra_names[:800],
        gender=gender,
        subject=subject,
        also_name=also_name,
        also_gender=also_gender,
        also_subject=also_subject,
        quantity=quantity,
        client_name=buyer["name"],
        client_email=buyer["email"],
        client_phone=buyer["phone"],
        client_address=buyer["address"],
        client_notes=buyer["notes"],
    )
    if created and ticket is not None:
        _schedule_new_order_notice(background, project, ticket, user)
    return UploadUrlOut(asset_id=asset_id, storage_key=key, upload_url="", expires_in=0)


@router.post("/{project_id}/extra-character", response_model=UploadUrlOut, status_code=201)
async def upload_extra_character(
    project_id: uuid.UUID,
    user: User = Depends(require_adult_user),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    name: str = "",
) -> UploadUrlOut:
    """Upload de foto de personagem extra (amigo, irmao, etc.)."""
    project = get_owned_project(db, user, project_id)
    data = await file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Arquivo vazio")
    if len(data) > 10_000_000:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Imagem muito grande (max. 10MB)"
        )
    data = _normalize_photo(data)
    key = storage.new_key(project.id, "extra_character", "jpg")
    storage.put_bytes(key, data, "image/jpeg")

    extras = list(project.extra_characters or [])
    extras.append(
        {
            "name": name.strip() or f"Personagem {len(extras) + 1}",
            "storage_key": key,
            "mime": "image/jpeg",
        }
    )
    project.extra_characters = extras
    db.commit()

    asset = Asset(
        project_id=project.id,
        kind="extra_character",
        storage_key=key,
        meta={"name": name.strip() or f"Personagem {len(extras)}"},
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return UploadUrlOut(asset_id=asset.id, storage_key=key, upload_url="", expires_in=0)
