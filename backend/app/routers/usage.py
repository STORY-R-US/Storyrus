"""Painel de gastos: agrega jobs.cost_usd. Protegido por senha no header."""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, time
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app import storage
from app.ai_clients.resilience import billing_exhausted
from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import (
    Asset,
    AssetKind,
    Job,
    JobType,
    OrderTicket,
    PrintOrder,
    Project,
    UsageEvent,
    User,
)
from app.order_tickets import backfill_order_tickets
from app.owner_auth import require_owner_password
from app.printkit.service import attach_service_orders
from app.schemas import (
    JobAcceptedOut,
    OrderFileOut,
    OrderTicketOut,
    UsageAnomalyOut,
    UsageBookOut,
    UsageBucketOut,
    UsageEventOut,
    UsageJobOut,
    UsageOut,
)
from app.services import jobs as jobs_svc
from app.services import preview_chain, spend_guard

from .projects.common import accept_job

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/usage", tags=["usage"])

_TZ = ZoneInfo("America/Sao_Paulo")
_BOOK_KINDS = (
    AssetKind.COVER.value,
    AssetKind.PAGE_IMAGE.value,
    AssetKind.IN_HAND.value,
    AssetKind.EBOOK.value,
)
_BOOK_LABELS = {
    AssetKind.COVER.value: "Capa",
    AssetKind.PAGE_IMAGE.value: "Página",
    AssetKind.IN_HAND.value: "Livro na mão",
    AssetKind.EBOOK.value: "PDF do livro",
}


def _preview_image_count(files: list[OrderFileOut]) -> int:
    return sum(file.kind in {"cover", "page_image", "in_hand"} for file in files)


def _generation_view(
    latest: Job | None,
    files: list[OrderFileOut],
    provider: str | None,
    result: dict,
) -> tuple[str, str | None, str | None]:
    """Selo da prévia, erro para mostrar e provedor.

    A história entra na fila depois das imagens. Ela não pode apagar a prévia
    nem deixar um livro pronto como se ainda estivesse na fila.
    """
    images = _preview_image_count(files)
    if latest is None:
        return ("ready" if files else "queued", None, provider)
    if latest.status == "PENDING":
        return ("queued", None, provider)
    if latest.status == "RUNNING":
        return ("generating", None, provider)
    error = _opt_str(latest.error) if latest.status == "FAILED" else None
    if error and billing_exhausted(error):
        error = None
    if latest.status == "FAILED":
        if images and latest.type == "STORY":
            return ("ready", error, provider)
        if images:
            return ("partial", error, provider)
        return ("failed", error, provider)
    if latest.type == "EBOOK":
        if provider == "demo" or (
            provider is None
            and latest.cost_usd == 0
            and _meta_dict(result.get("payload")).get("preview_chain")
        ):
            return ("demo", None, "demo")
        if result.get("preview_complete") is False:
            return ("partial", None, provider)
        return ("ready", None, provider)
    if images >= 3:
        return ("ready", None, provider)
    if images:
        return ("partial", None, provider)
    return ("queued", None, provider)


def _signed(key: str | None) -> str | None:
    if not key:
        return None
    try:
        return storage.presign_get(key)
    except Exception:
        return None


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _as_float(value) -> float | None:
    if value is None:
        return None
    return float(value)


def _parse_day(value: date | None, *, end: bool) -> datetime | None:
    if value is None:
        return None
    local = datetime.combine(value, time.max if end else time.min, tzinfo=_TZ)
    return local.astimezone(UTC)


def _event_rows(
    db: Session, range_start: datetime, range_end: datetime, job_rows
) -> list[UsageEventOut]:
    events = db.execute(
        select(UsageEvent, Project)
        .join(Project, Project.id == UsageEvent.project_id)
        .order_by(UsageEvent.created_at.desc())
        .limit(2000)
    ).all()
    out: list[UsageEventOut] = []
    jobs_with_lines: set = set()
    for event, project in events:
        created = _aware(event.created_at)
        if not (range_start <= created <= range_end):
            continue
        if event.job_id is not None:
            jobs_with_lines.add(event.job_id)
        out.append(
            UsageEventOut(
                id=event.id,
                job_id=event.job_id,
                project_id=event.project_id,
                child_name=project.child_name,
                kind=event.kind,
                provider=event.provider,
                action=event.action,
                label=event.label,
                cost_usd=_as_float(event.cost_usd),
                created_at=created,
            )
        )
        if len(out) >= 400:
            break
    for job, project in job_rows:
        created = _aware(job.created_at)
        if not (range_start <= created <= range_end):
            continue
        if job.id in jobs_with_lines:
            continue
        if job.cost_usd is None:
            continue
        out.append(
            UsageEventOut(
                id=None,
                job_id=job.id,
                project_id=job.project_id,
                child_name=project.child_name,
                kind="job",
                provider=job.provider or "desconhecido",
                action="job_total",
                label="Job sem extrato (antes do ledger)",
                cost_usd=_as_float(job.cost_usd),
                created_at=created,
            )
        )
    out.sort(key=lambda e: e.created_at, reverse=True)
    return out[:400]


def _meta_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _text(value) -> str:
    return value if isinstance(value, str) else ""


def _opt_str(value) -> str | None:
    if value is None:
        return None
    return value if isinstance(value, str) else str(value)


def _opt_int(value) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _created(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    return _aware(value)


def _give_up(db: Session, action: str) -> None:
    logger.exception("pedidos: %s", action)
    db.rollback()


def _load_orders(db: Session, user_id: uuid.UUID | None = None) -> list[OrderTicket]:
    stmt = select(OrderTicket).order_by(OrderTicket.created_at.desc()).limit(200)
    if user_id is not None:
        stmt = stmt.join(Project, Project.id == OrderTicket.project_id).where(
            Project.user_id == user_id
        )
    return list(db.scalars(stmt).all())


def _collect_orders(
    db: Session,
    *,
    user_id: uuid.UUID | None = None,
    backfill: bool = True,
) -> tuple[list[OrderTicketOut], int, int, int]:
    """Pedidos do painel, sem ler arquivos no storage.

    Um pedido com metadado torto, ou uma OS que não abre, não pode derrubar a lista.

    `user_id` limita a lista aos pedidos da própria conta (tela "Meus Pedidos" de
    quem não é admin). Nesse caso recupera só os pedidos dessa conta.
    """
    if backfill:
        try:
            backfill_order_tickets(db, prepare=False, user_id=user_id)
        except Exception:
            _give_up(db, "backfill")
    projects_total = int(db.scalar(select(func.count()).select_from(Project)) or 0)
    users_total = int(db.scalar(select(func.count()).select_from(User)) or 0)
    ticketed_ids = select(OrderTicket.project_id)
    projects_awaiting_photo = int(
        db.scalar(select(func.count()).select_from(Project).where(~Project.id.in_(ticketed_ids)))
        or 0
    )
    order_rows = _load_orders(db, user_id)
    try:
        attach_service_orders(
            db,
            [ticket.project for ticket in order_rows if ticket.project is not None],
            prepare=False,
        )
    except Exception:
        _give_up(db, "abrir ordem de serviço")
        order_rows = _load_orders(db, user_id)
    project_ids = [ticket.project_id for ticket in order_rows]
    # Read one pipeline job per listed project, never the global spend report.
    ranked_jobs = (
        select(
            Job.id,
            func.row_number()
            .over(partition_by=Job.project_id, order_by=(Job.created_at.desc(), Job.id.desc()))
            .label("position"),
        )
        .where(Job.project_id.in_(project_ids), Job.type.in_(["AVATAR", "STORY", "EBOOK"]))
        .subquery()
    )
    latest_jobs = (
        {
            job.project_id: job
            for job in db.scalars(
                select(Job)
                .join(ranked_jobs, ranked_jobs.c.id == Job.id)
                .where(ranked_jobs.c.position == 1)
            ).all()
        }
        if project_ids
        else {}
    )
    try:
        photo_rows = (
            db.scalars(
                select(Asset)
                .where(
                    Asset.project_id.in_(project_ids),
                    Asset.kind.in_([AssetKind.PHOTO.value, "extra_character"]),
                )
                .order_by(Asset.created_at.asc())
            ).all()
            if project_ids
            else []
        )
    except Exception:
        _give_up(db, "fotos")
        photo_rows = []
        order_rows = _load_orders(db, user_id)
    photos_by_project: dict = defaultdict(list)
    for asset in photo_rows:
        try:
            url = storage.presign_get(asset.storage_key)
        except Exception:
            continue
        if isinstance(url, str) and url:
            photos_by_project[asset.project_id].append(url)
    try:
        print_rows = (
            db.scalars(select(PrintOrder).where(PrintOrder.project_id.in_(project_ids))).all()
            if project_ids
            else []
        )
    except Exception:
        _give_up(db, "impressos")
        print_rows = []
        order_rows = _load_orders(db, user_id)
    print_by_project = {row.project_id: row for row in print_rows}
    try:
        stored_files = (
            db.scalars(
                select(Asset)
                .where(
                    Asset.project_id.in_(project_ids),
                    Asset.kind.in_(_BOOK_KINDS),
                )
                .order_by(Asset.created_at.asc())
            ).all()
            if project_ids
            else []
        )
    except Exception:
        _give_up(db, "arquivos do livro")
        stored_files = []
        order_rows = _load_orders(db, user_id)
    books_by_project: dict = defaultdict(list)
    for asset in stored_files:
        try:
            label = _BOOK_LABELS.get(asset.kind, asset.kind)
            if asset.kind == AssetKind.PAGE_IMAGE.value:
                page = _meta_dict(asset.meta).get("page")
                if isinstance(page, int) and not isinstance(page, bool):
                    label = f"Página {page}"
                elif isinstance(page, str) and page.strip():
                    label = f"Página {page.strip()}"
            url = _signed(asset.storage_key)
            if isinstance(url, str) and url:
                books_by_project[asset.project_id].append(
                    OrderFileOut(
                        label=_text(label) or asset.kind,
                        url=url,
                        kind=asset.kind,
                        provider=_opt_str(_meta_dict(asset.meta).get("provider")),
                    )
                )
        except Exception:
            logger.exception("pedidos: arquivo %s", getattr(asset, "id", None))
            continue
    orders: list[OrderTicketOut] = []
    for ticket in order_rows:
        try:
            project = ticket.project
            printed = print_by_project.get(ticket.project_id)
            files = list(books_by_project.get(ticket.project_id, []))
            if project is not None:
                ref = project.character_ref if isinstance(project.character_ref, dict) else {}
                storage_key = ref.get("storage_key")
                character_url = _signed(storage_key if isinstance(storage_key, str) else None)
                if character_url:
                    files.insert(
                        0,
                        OrderFileOut(
                            label="Personagem",
                            url=character_url,
                            kind="character",
                            provider=_opt_str(ref.get("provider")),
                        ),
                    )
                ebook_key = project.ebook_url if isinstance(project.ebook_url, str) else None
                ebook_url = _signed(ebook_key)
                if ebook_url and not any(item.label == "PDF do livro" for item in files):
                    files.append(OrderFileOut(label="PDF do livro", url=ebook_url, kind="ebook"))
            latest = latest_jobs.get(ticket.project_id)
            result = _meta_dict(latest.result) if latest else {}
            provider = _opt_str(result.get("image_provider"))
            image_count = _preview_image_count(files)
            progress = _meta_dict(result.get("progress"))
            if latest and latest.type == "EBOOK" and isinstance(progress.get("done"), int):
                image_count = progress["done"]
            generation_status, generation_error, provider = _generation_view(
                latest, files, provider, result
            )
            orders.append(
                OrderTicketOut(
                    id=ticket.id,
                    project_id=ticket.project_id,
                    summary=_text(ticket.summary) or "Pedido",
                    created_at=_created(ticket.created_at),
                    child_age=_opt_int(project.child_age) if project else None,
                    book_size=_opt_str(project.book_size) if project else None,
                    cover_type=_opt_str(project.cover_type) if project else None,
                    style=_opt_str(project.style) if project else None,
                    photo_urls=photos_by_project.get(ticket.project_id, []),
                    has_story=bool(project and _text(project.story_text).strip()),
                    book_files=files,
                    generation_status=generation_status,
                    generation_stage=latest.type if latest else None,
                    generated_images=image_count,
                    image_provider=provider,
                    image_model=_opt_str(result.get("image_model")),
                    generation_error=generation_error,
                    credits_fallback=bool(
                        project and (project.book_profile or {}).get("credits_fallback")
                    ),
                    print_order_id=printed.id if printed else None,
                    print_code=_opt_str(printed.code) if printed else None,
                    print_status=_opt_str(printed.status) if printed else None,
                    block_reason=_opt_str(printed.block_reason) if printed else None,
                    tracking_code=_opt_str(printed.tracking_code) if printed else None,
                    payment_status=_opt_str(printed.payment_status) if printed else None,
                    amount_cents=_opt_int(printed.amount_cents) if printed else None,
                )
            )
        except Exception:
            logger.exception("pedidos: item %s", getattr(ticket, "id", None))
            continue
    return orders, users_total, projects_total, projects_awaiting_photo


@router.get("/orders/mine", response_model=list[OrderTicketOut])
def my_orders(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    response: Response,
) -> list[OrderTicketOut]:
    """Pedidos da própria conta (a lista geral é exclusiva do painel admin)."""
    response.headers["Cache-Control"] = "private, no-store"
    orders, _, _, _ = _collect_orders(db, user_id=user.id)
    return orders


@router.get("", response_model=UsageOut)
def get_usage(
    _: Annotated[None, Depends(require_owner_password)],
    db: Annotated[Session, Depends(get_db)],
    response: Response,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    scope: Annotated[str | None, Query()] = None,
) -> UsageOut:
    response.headers["Cache-Control"] = "private, no-store"
    now_local = datetime.now(_TZ)
    today_start = datetime.combine(now_local.date(), time.min, tzinfo=_TZ).astimezone(UTC)
    today_end = datetime.combine(now_local.date(), time.max, tzinfo=_TZ).astimezone(UTC)
    month_start = datetime.combine(
        now_local.date().replace(day=1), time.min, tzinfo=_TZ
    ).astimezone(UTC)

    range_start = _parse_day(from_date, end=False) or month_start
    range_end = _parse_day(to_date, end=True) or today_end
    if range_end < range_start:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Intervalo invalido")

    # Pedidos só precisa da lista. O relatório de 2000 jobs deixa o painel em "Abrindo…".
    if (scope or "").strip().lower() == "orders":
        orders, users_total, projects_total, awaiting = _collect_orders(db)
        return UsageOut(
            timezone="America/Sao_Paulo",
            from_at=range_start,
            to_at=range_end,
            today_usd=0.0,
            month_usd=0.0,
            range_usd=0.0,
            books_count=0,
            avg_book_usd=None,
            by_type=[],
            by_provider=[],
            books=[],
            recent_jobs=[],
            orders=orders,
            users_total=users_total,
            projects_total=projects_total,
            projects_awaiting_photo=awaiting,
        )

    rows = db.execute(
        select(Job, Project)
        .join(Project, Project.id == Job.project_id)
        .order_by(Job.created_at.desc())
        .limit(2000)
    ).all()

    today_usd = 0.0
    month_usd = 0.0
    range_usd = 0.0
    by_type: dict[str, list[float]] = defaultdict(list)
    by_provider: dict[str, list[float]] = defaultdict(list)
    books: dict = {}
    recent: list[UsageJobOut] = []

    for job, project in rows:
        created = _aware(job.created_at)
        usd = _as_float(job.cost_usd)
        in_range = range_start <= created <= range_end
        if today_start <= created <= today_end and usd is not None:
            today_usd += usd
        if created >= month_start and usd is not None:
            month_usd += usd
        if in_range:
            if usd is not None:
                range_usd += usd
                by_type[job.type].append(usd)
                by_provider[job.provider or "desconhecido"].append(usd)
            book = books.get(project.id)
            if book is None:
                book = {
                    "project_id": project.id,
                    "child_name": project.child_name,
                    "status": project.status,
                    "usd": 0.0,
                    "measured": False,
                    "unmeasured_jobs": 0,
                    "updated_at": _aware(job.updated_at or job.created_at),
                }
                books[project.id] = book
            if usd is None:
                book["unmeasured_jobs"] += 1
            else:
                book["usd"] += usd
                book["measured"] = True
            updated = _aware(job.updated_at or job.created_at)
            if updated > book["updated_at"]:
                book["updated_at"] = updated
                book["status"] = project.status
            if len(recent) < 40:
                recent.append(
                    UsageJobOut(
                        id=job.id,
                        project_id=job.project_id,
                        child_name=project.child_name,
                        type=job.type,
                        status=job.status,
                        provider=job.provider,
                        cost_usd=usd,
                        attempts=job.attempts,
                        created_at=created,
                    )
                )

    book_rows = [
        UsageBookOut(
            project_id=b["project_id"],
            child_name=b["child_name"],
            status=b["status"],
            usd=round(b["usd"], 4) if b["measured"] else None,
            unmeasured_jobs=b["unmeasured_jobs"],
            updated_at=b["updated_at"],
        )
        for b in sorted(books.values(), key=lambda x: x["updated_at"], reverse=True)
    ]
    measured_books = [b for b in book_rows if b.usd is not None]
    avg = (
        round(sum(b.usd or 0.0 for b in measured_books) / len(measured_books), 4)
        if measured_books
        else None
    )

    event_rows = _event_rows(db, range_start, range_end, rows)
    orders, users_total, projects_total, projects_awaiting_photo = _collect_orders(db)

    day = spend_guard.day_spend(db)
    flags = spend_guard.anomalies(db, today_usd=today_usd)
    usd_ceiling = float(settings.daily_spend_usd_ceiling or 0.0)
    credits_ceiling = int(settings.daily_credits_ceiling or 0)

    return UsageOut(
        timezone="America/Sao_Paulo",
        from_at=range_start,
        to_at=range_end,
        today_usd=round(today_usd, 4),
        month_usd=round(month_usd, 4),
        range_usd=round(range_usd, 4),
        books_count=len(book_rows),
        avg_book_usd=avg,
        by_type=[
            UsageBucketOut(key=k, usd=round(sum(v), 4), jobs=len(v))
            for k, v in sorted(by_type.items())
        ],
        by_provider=[
            UsageBucketOut(key=k, usd=round(sum(v), 4), jobs=len(v))
            for k, v in sorted(by_provider.items())
        ],
        books=book_rows,
        recent_jobs=recent,
        events=event_rows,
        events_count=len(event_rows),
        daily_spend_usd_ceiling=usd_ceiling if usd_ceiling > 0 else None,
        daily_credits_ceiling=credits_ceiling if credits_ceiling > 0 else None,
        today_credits=day.credits_spent,
        reserved_usd=round(day.reserved_usd, 4),
        anomalies=[
            UsageAnomalyOut(kind=a.kind, severity=a.severity, message=a.message) for a in flags
        ],
        orders=orders,
        users_total=users_total,
        projects_total=projects_total,
        projects_awaiting_photo=projects_awaiting_photo,
    )


@router.post("/orders/{order_id}/generate", response_model=JobAcceptedOut, status_code=202)
def regenerate_order_images(
    order_id: uuid.UUID,
    _: Annotated[None, Depends(require_owner_password)],
    db: Annotated[Session, Depends(get_db)],
) -> JobAcceptedOut:
    """Generate the preview again with the saved prompts, photos and story."""
    if settings.offline_fallback and not settings.skip_openai:
        raise HTTPException(503, "Ative a geração OpenAI antes de gerar as imagens deste pedido.")
    ticket = db.get(OrderTicket, order_id)
    if ticket is None or ticket.project is None:
        raise HTTPException(404, "Pedido não encontrado")
    project = ticket.project
    active = db.scalar(
        select(Job)
        .where(
            Job.project_id == project.id,
            Job.status.in_(["PENDING", "RUNNING"]),
            Job.type.in_(["AVATAR", "STORY", "EBOOK"]),
        )
        .order_by(Job.created_at.desc())
    )
    if active is not None:
        return accept_job(active)
    if not db.scalar(
        select(Asset.id)
        .where(
            Asset.project_id == project.id,
            Asset.kind == AssetKind.PHOTO.value,
        )
        .limit(1)
    ):
        raise HTTPException(400, "Envie uma foto antes de gerar as imagens")
    from app.printkit.service import invalidate_print

    printed = db.scalar(select(PrintOrder).where(PrintOrder.project_id == project.id))
    if printed and printed.payment_status == "paid":
        raise HTTPException(
            409, "O pedido faturado precisa de revisão antes de refazer as imagens."
        )
    invalidate_print(db, project)
    project.character_approved_at = None
    project.book_approved_at = None
    project.preview_notified_at = None
    from app.services import book_profile

    # Livro novo: a prévia é capa, livro aberto e leitura. O avatar antigo
    # exige uma etapa que esse pedido ainda não tem e a geração morre na hora.
    if book_profile.enabled(project):
        job = jobs_svc.enqueue_job(
            db,
            user=project.user,
            project=project,
            job_type=JobType.EBOOK,
            idempotency_key=f"order-preview-{project.id}-{uuid.uuid4()}",
            payload={preview_chain.PREVIEW_FLAG: True, "master_preview": True},
        )
        return accept_job(job)
    job = jobs_svc.enqueue_job(
        db,
        user=project.user,
        project=project,
        job_type=JobType.AVATAR,
        idempotency_key=f"order-preview-{project.id}-{uuid.uuid4()}",
        payload={preview_chain.PREVIEW_FLAG: True, "reuse_story": bool(project.story_text)},
    )
    return accept_job(job)


@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(
    order_id: uuid.UUID,
    _: Annotated[None, Depends(require_owner_password)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    """Exclui o pedido e o projeto do livro (fotos, história, arquivos e OS).

    Apaga os filhos em SQL direto, sem depender do cascade ORM nem do
    `ON DELETE CASCADE` do banco (que se comporta diferente entre o SQLite dos
    testes e o Postgres de produção). Sem o projeto, o `backfill_order_tickets`
    não recria o pedido na próxima abertura do painel.
    """
    ticket = db.get(OrderTicket, order_id)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido nao encontrado")
    project_id = ticket.project_id
    try:
        # Ordem: filhos antes do projeto. usage_events antes de jobs.
        for stmt in (
            delete(UsageEvent).where(UsageEvent.project_id == project_id),
            delete(Asset).where(Asset.project_id == project_id),
            delete(OrderTicket).where(OrderTicket.project_id == project_id),
            delete(PrintOrder).where(PrintOrder.project_id == project_id),
            delete(Job).where(Job.project_id == project_id),
            delete(Project).where(Project.id == project_id),
        ):
            db.execute(stmt.execution_options(synchronize_session=False))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("pedidos: excluir pedido %s", order_id)
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)
