"""Cópia marcada das prévias. O arquivo original permanece limpo para o livro pago."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app import storage
from app.workers import book_render

logger = logging.getLogger(__name__)

PREVIEW_ROLES = frozenset({"01_CAPA", "02_LIVRO_ABERTO", "03_LEITURA"})


def display_key(db: Session, asset) -> str:
    meta = asset.meta or {}
    if meta.get("role") not in PREVIEW_ROLES:
        return asset.storage_key
    cached = meta.get("watermark_key")
    if isinstance(cached, str) and cached:
        return cached
    try:
        marked = book_render.preview_watermark(storage.get_bytes(asset.storage_key))
    except Exception:
        logger.exception("marca da previa falhou")
        return asset.storage_key
    key = storage.new_key(asset.project_id, "preview-mark", "png")
    storage.put_bytes(key, marked, "image/png")
    updated = dict(meta)
    updated["watermark_key"] = key
    asset.meta = updated
    flag_modified(asset, "meta")
    db.commit()
    return key
