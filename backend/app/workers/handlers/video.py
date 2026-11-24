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


COVER_PROMPT = (
    "Anime suavemente esta capa de livro infantil ilustrado: o personagem respira, "
    "pisca e se mexe de leve, cabelo e roupas balançam com a brisa, nuvens, brilhos "
    "e estrelas se movem devagar ao fundo. Câmera quase parada com leve aproximação. "
    "Mantenha o rosto, as cores e todo o texto da capa fixos, nítidos e legíveis."
)


def _cover_reference_key(db: Session, project: Project) -> str:
    """Capa aprovada do Estúdio (sem marca d'água), no idioma do livro."""
    editorial = (project.book_profile or {}).get("editorial")
    language = project.language or "pt-BR"
    covers = [
        asset
        for asset in db.scalars(
            select(Asset)
            .where(Asset.project_id == project.id, Asset.kind == AssetKind.COVER.value)
            .order_by(Asset.created_at.desc())
        ).all()
        if (asset.meta or {}).get("workflow") == 1
        and (asset.meta or {}).get("role") == "01_CAPA"
        and (not editorial or (asset.meta or {}).get("editorial") == editorial)
    ]
    cover = next(
        (a for a in covers if (a.meta or {}).get("language") == language),
        covers[0] if covers else None,
    )
    if cover is None:
        raise ProviderError("Capa aprovada ausente para a capa animada", transient=False)
    return cover.storage_key


STORY_PROMPT = (
    "Anime suavemente esta página de livro infantil ilustrado: os personagens se mexem "
    "de leve e com naturalidade, respiram, piscam e sorriem; cabelo, roupas, água, "
    "folhas e nuvens balançam devagar. Câmera quase parada com leve aproximação. "
    "Mantenha os rostos, as cores e todo o texto da página fixos, nítidos e legíveis."
)


def _story_frames(db: Session, project: Project) -> list[tuple[str, str]]:
    """Capa, as páginas com texto (16 ou 20) e a contracapa do livro aprovado, em ordem."""
    language = project.language or "pt-BR"
    editorial = (project.book_profile or {}).get("editorial")
    rows = db.scalars(
        select(Asset).where(Asset.project_id == project.id).order_by(Asset.created_at.asc())
    ).all()

    def latest(role: str, page: int | None = None) -> Asset | None:
        found = None
        for asset in rows:
            meta = asset.meta or {}
            if meta.get("workflow") != 1 or meta.get("role") != role:
                continue
            if meta.get("language") not in (None, language):
                continue
            if editorial and meta.get("editorial") not in (None, editorial):
                continue
            if page is not None and meta.get("page") != page:
                continue
            found = asset
        return found

    cover = latest("01_CAPA")
    if cover is None:
        raise ProviderError("Capa aprovada ausente para a história animada", transient=False)
    frames = [("capa", (cover.meta or {}).get("flat_cover_key") or cover.storage_key)]
    from app.services.book_profile import page_count

    for number in range(1, page_count(project) + 1):
        page = latest("com_texto", number)
        if page is None:
            raise ProviderError(f"Página {number} ausente para a história animada", transient=False)
        frames.append((f"pagina-{number:02d}", page.storage_key))
    back = latest("04_CONTRACAPA")
    if back is not None:
        frames.append(("contracapa", back.storage_key))
    return frames


async def _download(url: str) -> bytes:
    import httpx

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content


def concat_clips(clips: list[bytes], *, size: int = 720, fps: int = 24) -> bytes:
    """Junta os clipes em sequência, com corte seco, num MP4 quadrado e sem áudio."""
    import subprocess
    import tempfile
    from pathlib import Path

    from app.media.assemble import ffmpeg_available

    if not ffmpeg_available():
        raise ProviderError("ffmpeg ausente para montar a história animada", transient=False)
    with tempfile.TemporaryDirectory() as tmp:
        cmd = ["ffmpeg", "-y", "-v", "error"]
        for i, blob in enumerate(clips):
            path = Path(tmp) / f"c{i:02d}.mp4"
            path.write_bytes(blob)
            cmd += ["-i", str(path)]
        norm = "".join(
            f"[{i}:v]scale={size}:{size}:force_original_aspect_ratio=decrease,"
            f"pad={size}:{size}:(ow-iw)/2:(oh-ih)/2,fps={fps},setsar=1,format=yuv420p[v{i}];"
            for i in range(len(clips))
        )
        joined = "".join(f"[v{i}]" for i in range(len(clips)))
        out = Path(tmp) / "historia.mp4"
        cmd += [
            "-filter_complex",
            f"{norm}{joined}concat=n={len(clips)}:v=1:a=0[out]",
            "-map",
            "[out]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "21",
            "-movflags",
            "+faststart",
            "-an",
            str(out),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise ProviderError(
                f"ffmpeg falhou ao montar a história: {(proc.stderr or '')[-500:]}",
                transient=False,
            )
        return out.read_bytes()


STORY_MAX_FAILURES = 3


async def _handle_story_video(db: Session, job: Job, project: Project) -> None:
    """História animada comprada: cada página vira um clipe Kling, montados em sequência.

    Não segura a fila: envia os clipes, confere uma vez e devolve o job para a
    fila (JobDeferred) até a Kling terminar. Clipes prontos ficam como Asset e
    são reaproveitados numa nova tentativa, sem pagar a Kling duas vezes.
    """
    from app.workers.deferral import JobDeferred

    if _pkg()._use_video_offline():
        raise ProviderError("Kling não configurada para a história animada", transient=False)
    frames = _story_frames(db, project)
    seconds = _clamp_kling_duration(settings.story_video_clip_s)
    if project.status != ProjectStatus.VIDEO_RUNNING.value:
        _set_status(db, project, ProjectStatus.VIDEO_RUNNING)
    done: dict[str, str] = {}
    for asset in db.scalars(
        select(Asset)
        .where(Asset.project_id == project.id, Asset.kind == AssetKind.VIDEO.value)
        .order_by(Asset.created_at.asc())
    ).all():
        meta = asset.meta or {}
        if meta.get("kind") == "story_clip" and meta.get("seconds") == seconds:
            done[meta.get("source_key")] = asset.storage_key
    state = dict((job.result or {}).get("story") or {})
    tasks: dict[str, str] = dict(state.get("tasks") or {})
    failures: dict[str, int] = dict(state.get("failures") or {})
    cost = float(state.get("cost_usd") or 0.0)
    provider = _pkg().get_video_provider(_payload(job).get("provider") or job.provider)

    def save() -> None:
        job.result = {
            **(job.result or {}),
            "story": {"tasks": tasks, "failures": failures, "cost_usd": round(cost, 6)},
            "progress": {
                "stage": "story_video",
                "done": sum(1 for _, k in frames if k in done),
                "total": len(frames),
            },
        }
        job.cost_usd = round(cost, 6)
        db.commit()

    for label, key in frames:
        task_id = tasks.get(key)
        if key in done or not task_id:
            continue
        task = await provider.poll_video(provider_task_id=task_id)
        if task.status == "DONE" and task.video_url:
            blob = await _download(task.video_url)
            clip_key = storage.new_key(project.id, AssetKind.VIDEO.value, "mp4")
            storage.put_bytes(clip_key, blob, "video/mp4")
            db.add(
                Asset(
                    project_id=project.id,
                    kind=AssetKind.VIDEO.value,
                    storage_key=clip_key,
                    meta={
                        "kind": "story_clip",
                        "frame": label,
                        "source_key": key,
                        "seconds": seconds,
                    },
                )
            )
            done[key] = clip_key
            tasks.pop(key, None)
            billed = getattr(task, "cost_usd", None)
            cost += billed if billed is not None else video_cost(seconds)
            save()
        elif task.status == "FAILED":
            tasks.pop(key, None)
            failures[key] = failures.get(key, 0) + 1
            save()
            if failures[key] >= STORY_MAX_FAILURES:
                raise ProviderError(
                    f"A Kling não conseguiu animar {label} "
                    f"depois de {STORY_MAX_FAILURES} tentativas",
                    transient=False,
                )

    slots = max(1, int(settings.story_video_concurrency)) - len(tasks)
    for label, key in frames:
        if slots <= 0:
            break
        if key in done or key in tasks:
            continue
        task = await provider.create_video(
            image=storage.get_bytes(key), prompt=STORY_PROMPT, duration_s=seconds
        )
        tasks[key] = task.provider_task_id
        slots -= 1
        save()

    if any(key not in done for _, key in frames):
        save()
        raise JobDeferred(settings.story_video_poll_s)

    movie = concat_clips([storage.get_bytes(done[key]) for _, key in frames])
    video_key = storage.new_key(project.id, AssetKind.VIDEO.value, "mp4")
    storage.put_bytes(video_key, movie, "video/mp4")
    db.add(
        Asset(
            project_id=project.id,
            kind=AssetKind.VIDEO.value,
            storage_key=video_key,
            meta={"kind": "story_video", "clips": len(frames), "seconds": seconds},
        )
    )
    project.video_url = video_key
    save()
    _set_status(db, project, ProjectStatus.VIDEO_READY)


async def handle_video(db: Session, job: Job) -> None:
    """Animação curta (Kling image2video) — não é o vídeo narrado longo."""
    import asyncio
    import time

    project = _project(db, job)
    payload = _payload(job)
    if payload.get("source") == "story":
        await _handle_story_video(db, job, project)
        return
    from_cover = payload.get("source") == "cover"
    sb = None if from_cover else _latest_storyboard(db, project)
    ref_key = (
        _cover_reference_key(db, project)
        if from_cover
        else _video_reference_key(db, project, scene_n=1)
    )
    if from_cover and _pkg()._use_video_offline():
        # Item pago: sem a Kling configurada, falha em vez de entregar um GIF de teste.
        raise ProviderError("Kling não configurada para a capa animada", transient=False)
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

        prompt = (
            COVER_PROMPT if from_cover else "Anime o personagem com movimento suave e expressivo."
        )
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
            meta={
                "source": source_url,
                "kind": "animated_cover" if from_cover else "animation",
            },
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
