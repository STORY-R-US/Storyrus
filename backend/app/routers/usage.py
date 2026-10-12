"""Painel de gastos: agrega jobs.cost_usd. Protegido por senha no header."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, time
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import storage
from app.config import settings
from app.database import get_db
from app.models import Asset, AssetKind, Job, OrderTicket, PrintOrder, Project, UsageEvent, User
from app.order_tickets import backfill_order_tickets
from app.owner_auth import require_owner_password
from app.printkit.service import attach_service_orders
from app.schemas import (
    OrderFileOut,
    OrderTicketOut,
    UsageAnomalyOut,
    UsageBookOut,
    UsageBucketOut,
    UsageEventOut,
    UsageJobOut,
    UsageOut,
)
from app.services import spend_guard

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


def _collect_orders(db: Session) -> tuple[list[OrderTicketOut], int, int, int]:
    """Pedidos do painel, sem ler arquivos no storage."""
    backfill_order_tickets(db, prepare=False)
    projects_total = int(db.scalar(select(func.count()).select_from(Project)) or 0)
    users_total = int(db.scalar(select(func.count()).select_from(User)) or 0)
    ticketed_ids = select(OrderTicket.project_id)
    projects_awaiting_photo = int(
        db.scalar(select(func.count()).select_from(Project).where(~Project.id.in_(ticketed_ids)))
        or 0
    )
    order_rows = db.scalars(
        select(OrderTicket).order_by(OrderTicket.created_at.desc()).limit(200)
    ).all()
    attach_service_orders(
        db,
        [ticket.project for ticket in order_rows if ticket.project is not None],
        prepare=False,
    )
    project_ids = [ticket.project_id for ticket in order_rows]
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
    photos_by_project: dict = defaultdict(list)
    for asset in photo_rows:
        try:
            url = storage.presign_get(asset.storage_key)
        except Exception:
            continue
        if url:
            photos_by_project[asset.project_id].append(url)
    print_rows = (
        db.scalars(select(PrintOrder).where(PrintOrder.project_id.in_(project_ids))).all()
        if project_ids
        else []
    )
    print_by_project = {row.project_id: row for row in print_rows}
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
    books_by_project: dict = defaultdict(list)
    for asset in stored_files:
        label = _BOOK_LABELS.get(asset.kind, asset.kind)
        if asset.kind == AssetKind.PAGE_IMAGE.value:
            page = (asset.meta or {}).get("page")
            if page:
                label = f"Página {page}"
        url = _signed(asset.storage_key)
        if url:
            books_by_project[asset.project_id].append(OrderFileOut(label=label, url=url))
    orders: list[OrderTicketOut] = []
    for ticket in order_rows:
        project = ticket.project
        printed = print_by_project.get(ticket.project_id)
        files = list(books_by_project.get(ticket.project_id, []))
        if project is not None:
            ref = project.character_ref if isinstance(project.character_ref, dict) else {}
            character_url = _signed(ref.get("storage_key"))
            if character_url:
                files.insert(0, OrderFileOut(label="Personagem", url=character_url))
            ebook_url = _signed(project.ebook_url)
            if ebook_url and not any(item.label == "PDF do livro" for item in files):
                files.append(OrderFileOut(label="PDF do livro", url=ebook_url))
        orders.append(
            OrderTicketOut(
                id=ticket.id,
                project_id=ticket.project_id,
                summary=ticket.summary,
                created_at=_aware(ticket.created_at),
                child_age=project.child_age if project else None,
                book_size=project.book_size if project else None,
                cover_type=project.cover_type if project else None,
                style=project.style if project else None,
                photo_urls=photos_by_project.get(ticket.project_id, []),
                has_story=bool(project and (project.story_text or "").strip()),
                book_files=files,
                print_order_id=printed.id if printed else None,
                print_code=printed.code if printed else None,
                print_status=printed.status if printed else None,
                block_reason=printed.block_reason if printed else None,
                tracking_code=printed.tracking_code if printed else None,
                payment_status=printed.payment_status if printed else None,
                amount_cents=printed.amount_cents if printed else None,
            )
        )
    return orders, users_total, projects_total, projects_awaiting_photo


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
