"""Video job handler (Kling image2video)."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import storage
from app.ai_clients.base import ProviderError
from app.config import settings
from app.models import Asset, AssetKind, Job, Project, ProjectStatus
from app.services.pricing import video_cost

from .common import (
    _offline_gif,
    _payload,
    _project,
    _set_status,
)
from .story import _latest_storyboard

logger = logging.getLogger("worker")


def _pkg():
    """Package root — tests monkeypatch providers/score on app.workers.handlers."""
    from app.workers import handlers as pkg

    return pkg


def _kling_configured() -> bool:
    if settings.kling_api_key:
        return True
    return bool(settings.kling_access_key and settings.kling_secret_key)


def _use_video_offline() -> bool:
    """GIF offline quando não há chaves Kling; com chaves, sempre usa o provedor real."""
    return not _kling_configured()


def _clamp_kling_duration(duration_s: int) -> int:
    """Kling aceita apenas 5s ou 10s."""
    return 10 if int(duration_s) >= 8 else 5


def _video_reference_key(db: Session, project: Project, *, scene_n: int = 1) -> str:
    """Imagem base da animação: keyframe da cena, senão o avatar 3D (character_ref)."""
    page_assets = db.scalars(
        select(Asset)
        .where(Asset.project_id == project.id, Asset.kind == AssetKind.PAGE_IMAGE.value)
        .order_by(Asset.created_at.desc())
    ).all()
    for asset in page_assets:
        meta = asset.meta or {}
        if meta.get("keyframe") == scene_n:
            return asset.storage_key

    if project.character_ref and project.character_ref.get("storage_key"):
        return project.character_ref["storage_key"]
    raise ProviderError(
        "Imagem de referencia ausente: gere e aprove o personagem antes",
        transient=False,
    )


async def handle_video(db: Session, job: Job) -> None:
    """Animação curta (Kling image2video) — não é o vídeo narrado longo."""
    import asyncio
    import time

    project = _project(db, job)
    payload = _payload(job)
    sb = _latest_storyboard(db, project)
    ref_key = _video_reference_key(db, project, scene_n=1)
    _set_status(db, project, ProjectStatus.VIDEO_RUNNING)

    base_image = storage.get_bytes(ref_key)
    source_url: str | None = None
    task = None
    if _pkg()._use_video_offline():
        video_key = storage.new_key(project.id, AssetKind.VIDEO.value, "gif")
        video_label = "Animacao offline"
        if sb and sb.get("scenes"):
            video_label = (sb["scenes"][0].get("video_prompt") or video_label)[:32]
        storage.put_bytes(video_key, _offline_gif(video_label), "image/gif")
        stored = video_key
        source_url = "offline:local"
    else:
        provider = _pkg().get_video_provider(payload.get("provider") or job.provider)

        prompt = "Anime o personagem com movimento suave e expressivo."
        if sb and sb.get("scenes"):
            first = sb["scenes"][0]
            prompt = first.get("video_prompt") or prompt

        duration_s = _clamp_kling_duration(
            int(payload.get("duration_s", settings.default_video_duration_s))
        )
        task = await provider.create_video(
            image=base_image,
            prompt=prompt,
            duration_s=duration_s,
        )
        job.result = {**(job.result or {}), "provider_task_id": task.provider_task_id}
        db.commit()

        deadline = time.monotonic() + settings.video_poll_timeout_s
        while task.status not in ("DONE", "FAILED"):
            if time.monotonic() > deadline:
                raise ProviderError("Timeout aguardando video", transient=True)
            await asyncio.sleep(settings.video_poll_interval_s)
            task = await provider.poll_video(provider_task_id=task.provider_task_id)

        if task.status == "FAILED" or not task.video_url:
            raise ProviderError("Provedor de video falhou", transient=True)

        video_key = storage.new_key(project.id, AssetKind.VIDEO.value, "mp4")
        try:
            import httpx

            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.get(task.video_url)
                resp.raise_for_status()
                storage.put_bytes(video_key, resp.content, "video/mp4")
                stored = video_key
                source_url = task.video_url
        except Exception:  # noqa: BLE001 - se nao der para baixar, guarda a URL do provedor
            stored = task.video_url
            source_url = task.video_url

    db.add(
        Asset(
            project_id=project.id,
            kind=AssetKind.VIDEO.value,
            storage_key=stored,
            meta={"source": source_url, "kind": "animation"},
        )
    )
    project.video_url = stored
    if _pkg()._use_video_offline():
        job.cost_usd = 0.0
    else:
        billed = getattr(task, "cost_usd", None)
        duration_s = _clamp_kling_duration(
            int(payload.get("duration_s", settings.default_video_duration_s))
        )
        job.cost_usd = billed if billed is not None else video_cost(duration_s)
    _set_status(db, project, ProjectStatus.VIDEO_READY)


def _scene_image_bytes(db: Session, project: Project, scene_n: int) -> bytes:
    """Imagem da cena: keyframe, senão page_image por ordem, senão character."""
    try:
        key = _video_reference_key(db, project, scene_n=scene_n)
        return storage.get_bytes(key)
    except ProviderError:
        pass
    pages = db.scalars(
        select(Asset)
        .where(Asset.project_id == project.id, Asset.kind == AssetKind.PAGE_IMAGE.value)
        .order_by(Asset.created_at.asc())
    ).all()
    # Páginas sem meta keyframe (ebook) — usa índice 0-based
    non_kf = [a for a in pages if not (a.meta or {}).get("keyframe")]
    if non_kf:
        idx = max(0, min(scene_n - 1, len(non_kf) - 1))
        return storage.get_bytes(non_kf[idx].storage_key)
    if pages:
        idx = max(0, min(scene_n - 1, len(pages) - 1))
        return storage.get_bytes(pages[idx].storage_key)
    if project.character_ref and project.character_ref.get("storage_key"):
        return storage.get_bytes(project.character_ref["storage_key"])
    raise ProviderError("Sem imagens para montar o video narrado", transient=False)
