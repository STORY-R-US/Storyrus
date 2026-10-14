"""Abre/atualiza o pedido do dono (order_tickets) quando há foto no projeto."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Asset, AssetKind, OrderTicket, Project, User
from app.orders import build_book_order_summary, client_registration, parse_extra_names


def _stored_extra_names(project: Project) -> list[str]:
    raw = project.extra_characters or []
    if isinstance(raw, dict):
        raw = [raw]
    names: list[str] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict) and item.get("name"):
                names.append(str(item["name"]))
    return names


def _copy_count(raw: str) -> int | None:
    text = (raw or "").strip()
    if not text.isdigit():
        return None
    count = int(text)
    if count < 1 or count > 500:
        return None
    return count


def buyer_from_user(user: User) -> dict[str, str] | None:
    """Monta o cadastro do cliente a partir do perfil da conta."""
    address = ", ".join(
        part
        for part in (
            (user.street or "").strip(),
            (user.number or "").strip(),
            (user.complement or "").strip(),
            (user.district or "").strip(),
            (user.city or "").strip(),
            (user.state or "").strip(),
            (user.country or "").strip(),
            (user.postal_code or "").strip(),
        )
        if part
    )
    return client_registration(
        name=(user.full_name or "").strip() or user.email,
        email=user.email,
        phone=(user.phone or "").strip(),
        address=address,
        notes="",
    )


def resolve_buyer(
    user: User,
    *,
    client_name: str = "",
    client_email: str = "",
    client_phone: str = "",
    client_address: str = "",
    client_notes: str = "",
) -> dict[str, str]:
    """Prefer form fields; otherwise perfil da conta; senão e-mail da conta."""
    from app.security import is_guest_user

    buyer = client_registration(
        name=client_name,
        email=client_email,
        phone=client_phone,
        address=client_address,
        notes=client_notes,
    )
    if buyer is not None:
        return buyer
    profile = buyer_from_user(user)
    if profile is not None:
        return profile
    if not is_guest_user(email=user.email, password_hash=user.password_hash):
        return {
            "name": (user.full_name or "").strip() or user.email,
            "email": user.email,
            "phone": (user.phone or "").strip(),
            "address": "",
            "notes": "",
        }
    raise ValueError("Cadastro do cliente incompleto")


def register_order_ticket(
    db: Session,
    project: Project,
    *,
    language: str = "",
    theme_label: str = "",
    extra_names: str = "",
    gender: str = "",
    subject: str = "",
    also_name: str = "",
    also_gender: str = "",
    also_subject: str = "",
    quantity: str = "",
    client_name: str = "",
    client_email: str = "",
    client_phone: str = "",
    client_address: str = "",
    client_notes: str = "",
    prepare: bool = True,
) -> tuple[OrderTicket, bool]:
    """Cria ou atualiza o pedido do projeto (um por projeto).

    Retorna `(ticket, created)`: `created` indica pedido novo, para o time ser
    avisado uma única vez (não a cada foto).
    """
    lang = (language or "").strip() or (project.language or "pt-BR")
    if len(lang) <= 8:
        project.language = lang
    theme = (theme_label or "").strip()[:500] or (project.theme or "")
    extras = parse_extra_names(extra_names) + parse_extra_names(
        ", ".join(_stored_extra_names(project))
    )
    photo_count = db.scalar(
        select(func.count())
        .select_from(Asset)
        .where(
            Asset.project_id == project.id,
            Asset.kind.in_([AssetKind.PHOTO.value, "extra_character"]),
        )
    )
    summary = build_book_order_summary(
        style=project.style,
        child_name=project.child_name,
        language=lang,
        theme=theme,
        extra_names=extras,
        photo_count=max(int(photo_count or 0), 1),
        dedication=project.dedication,
        gender=gender,
        subject=subject,
        also_name=also_name,
        also_gender=also_gender,
        also_subject=also_subject,
        quantity=_copy_count(quantity),
        client_name=client_name,
        client_email=client_email,
        client_phone=client_phone,
        client_address=client_address,
        client_notes=client_notes,
    )
    existing = db.scalar(select(OrderTicket).where(OrderTicket.project_id == project.id))
    if existing is not None:
        existing.summary = summary
        db.add(existing)
        ticket = existing
        created = False
    else:
        ticket = OrderTicket(project_id=project.id, summary=summary)
        db.add(ticket)
        db.flush()
        created = True
    from app.printkit.service import open_print_order

    open_print_order(db, project, requested=False, prepare=prepare)
    return ticket, created


def backfill_order_tickets(db: Session, *, prepare: bool = False) -> int:
    """Abre pedidos faltantes para projetos que já têm foto (mobile/presign/falha).

    Não gera PDF: quem lista o painel não pode ficar lendo cada imagem.
    """
    ticketed = select(OrderTicket.project_id)
    photo_projects = db.scalars(
        select(Project)
        .where(
            Project.id.in_(
                select(Asset.project_id).where(
                    Asset.kind.in_([AssetKind.PHOTO.value, "extra_character"])
                )
            ),
            ~Project.id.in_(ticketed),
        )
        .limit(200)
    ).all()
    created = 0
    for project in photo_projects:
        user = project.user
        if user is None:
            continue
        try:
            buyer = resolve_buyer(user)
        except ValueError:
            buyer = {
                "name": (user.full_name or "").strip() or user.email,
                "email": user.email,
                "phone": (user.phone or "").strip(),
                "address": "",
                "notes": "",
            }
        register_order_ticket(
            db,
            project,
            language=project.language or "pt-BR",
            theme_label=project.theme or "",
            client_name=buyer["name"],
            client_email=buyer["email"],
            client_phone=buyer["phone"],
            client_address=buyer["address"],
            client_notes=buyer["notes"],
            prepare=prepare,
        )
        created += 1
    if created:
        db.commit()
    return created
