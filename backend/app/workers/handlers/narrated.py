"""Narrated video job handler."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import storage
from app.ai_clients.base import ProviderError
from app.config import settings
from app.models import Asset, AssetKind, Job, ProjectStatus, UserVoice

from .common import _payload, _project, _set_status
from .story import _latest_storyboard
from .video import _scene_image_bytes

logger = logging.getLogger("worker")


def _resolve_elevenlabs_voice_id(db: Session, user_id: uuid.UUID, payload: dict) -> str | None:
    """Resolve voice_id interno do payload (ou default do usuário) para ID ElevenLabs."""
    voice_uuid = None
    raw = (payload or {}).get("voice_id")
    if raw:
        try:
            voice_uuid = uuid.UUID(str(raw))
        except (ValueError, TypeError):
            voice_uuid = None
    if voice_uuid is not None:
        voice = db.get(UserVoice, voice_uuid)
        if voice and voice.user_id == user_id:
            return voice.elevenlabs_voice_id
    default = db.scalar(
        select(UserVoice).where(UserVoice.user_id == user_id, UserVoice.is_default.is_(True))
    )
    if default:
        return default.elevenlabs_voice_id
    return None


async def handle_narrated_video(db: Session, job: Job) -> None:
    """Vídeo narrado multi-cena: TTS + Ken Burns (ffmpeg) a partir do storyboard."""
    from app.media.assemble import (
        AssembleError,
        SceneClip,
        assemble_narrated_video,
        assemble_slideshow_gif,
        ffmpeg_available,
    )
    from app.media.tts import TtsError, get_tts_provider

    project = _project(db, job)
    sb = _latest_storyboard(db, project)
    if not sb or not sb.get("scenes"):
        raise ProviderError(
            "Storyboard ausente: aguarde a geracao do roteiro ou rode STORYBOARD",
            transient=False,
        )

    _set_status(db, project, ProjectStatus.VIDEO_RUNNING)
    language = project.language or sb.get("language") or "pt-BR"
    el_voice_id = _resolve_elevenlabs_voice_id(db, project.user_id, _payload(job))
    tts = get_tts_provider(voice_id=el_voice_id)
    clips: list[SceneClip] = []

    for sc in sb["scenes"]:
        n = int(sc.get("n") or len(clips) + 1)
        narration = (sc.get("narration") or "").strip() or f"Cena {n}."
        try:
            audio = await tts.synthesize(narration, language=language)
        except TtsError as exc:
            if not settings.offline_fallback:
                raise ProviderError(str(exc), transient=exc.transient) from exc
            # Tom curto silencioso via edge falhou — usa beep mínimo (áudio vazio gera GIF)
            audio = b""
        image = _scene_image_bytes(db, project, n)
        if not audio:
            # Sem áudio: ainda entra no fallback GIF
            clips.append(SceneClip(image_bytes=image, audio_bytes=b"\x00" * 0, image_ext="png"))
        else:
            clips.append(SceneClip(image_bytes=image, audio_bytes=audio, image_ext="png"))

    # Descarta cenas sem áudio válido se ffmpeg estiver disponível
    usable = [c for c in clips if c.audio_bytes]
    music = None
    # app/assets/... — package lives at app/workers/handlers/
    music_path = Path(__file__).resolve().parents[2] / "assets" / "audio" / "bed.mp3"
    if music_path.is_file():
        music = music_path.read_bytes()

    try:
        if ffmpeg_available() and usable:
            video_bytes = assemble_narrated_video(usable, music_bytes=music)
            ext, mime = "mp4", "video/mp4"
        else:
            video_bytes = assemble_slideshow_gif(clips or usable)
            ext, mime = "gif", "image/gif"
    except AssembleError as exc:
        if settings.offline_fallback:
            video_bytes = assemble_slideshow_gif(clips)
            ext, mime = "gif", "image/gif"
        else:
            raise ProviderError(str(exc), transient=False) from exc

    key = storage.new_key(project.id, AssetKind.NARRATED_VIDEO.value, ext)
    storage.put_bytes(key, video_bytes, mime)
    db.add(
        Asset(
            project_id=project.id,
            kind=AssetKind.NARRATED_VIDEO.value,
            storage_key=key,
            meta={"scenes": len(sb["scenes"]), "mime": mime},
        )
    )
    project.narrated_video_url = key
    job.cost_usd = 0.0
    # Não sobrescreve VIDEO_READY da animação se já existir — usa status genérico pronto
    if project.status != ProjectStatus.VIDEO_READY.value:
        _set_status(db, project, ProjectStatus.VIDEO_READY)
    else:
        db.commit()
