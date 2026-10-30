"""Adult authorization for media; this is not verifiable parental consent."""

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select

from app.models import Asset, AssetKind, Project

NOTICE_VERSION = "2026-10-29"


def photos_authorized(db, project_id) -> bool:
    if db.scalar(select(Project.processing_revoked_at).where(Project.id == project_id)):
        return False
    records = db.scalars(
        select(Asset.meta).where(
            Asset.project_id == project_id,
            Asset.kind.in_([AssetKind.PHOTO.value, "extra_character"]),
        )
    ).all()
    return all(
        ((meta or {}).get("adult_authorization") or {}).get("notice_version") == NOTICE_VERSION
        for meta in records
    )


def require_photo_authorization(db, project_id) -> None:
    if not photos_authorized(db, project_id):
        raise HTTPException(
            403,
            "Confirme a autorização atual do responsável antes de gerar novos materiais com estas fotos.",
        )


def media_authorization(user, *, confirmed: bool, version: str, scope: str) -> dict:
    if not confirmed or version != NOTICE_VERSION:
        raise HTTPException(
            403,
            "Leia o aviso de privacidade e confirme a autorização do responsável adulto antes de enviar arquivos.",
        )
    return {
        "notice_version": NOTICE_VERSION,
        "accepted_at": datetime.now(UTC).isoformat(),
        "adult_user_id": str(user.id),
        "scope": scope,
        "method": "adult_account_explicit_authorization",
    }
