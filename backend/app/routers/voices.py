"""Vozes personalizadas reutilizáveis (ElevenLabs Instant Voice Clone)."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import storage
from app.database import get_db
from app.deps import get_current_user, require_registered_user
from app.media.tts import (
    TtsError,
    clone_voice,
    delete_cloned_voice,
    elevenlabs_configured,
)
from app.models import User, UserVoice

router = APIRouter(prefix="/v1/voices", tags=["voices"])

MAX_BYTES = 10 * 1024 * 1024
ALLOWED_MIME = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/webm",
    "audio/ogg",
    "application/ogg",
}
EXT_BY_MIME = {
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/wave": "wav",
    "audio/mp4": "m4a",
    "audio/m4a": "m4a",
    "audio/x-m4a": "m4a",
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "application/ogg": "ogg",
}


class VoiceOut(BaseModel):
    id: uuid.UUID
    name: str
    is_default: bool
    mime_type: str
    created_at: object

    model_config = {"from_attributes": True}


class VoiceListOut(BaseModel):
    items: list[VoiceOut]
    custom_voice_available: bool


class VoicePatchIn(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    is_default: bool | None = None


def _voice_out(v: UserVoice) -> VoiceOut:
    return VoiceOut(
        id=v.id,
        name=v.name,
        is_default=v.is_default,
        mime_type=v.mime_type,
        created_at=v.created_at,
    )


def _guess_mime(filename: str | None, content_type: str | None) -> str:
    mime = (content_type or "").split(";")[0].strip().lower()
    if mime in ALLOWED_MIME:
        return mime
    ext = Path(filename or "").suffix.lower().lstrip(".")
    by_ext = {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "m4a": "audio/mp4",
        "mp4": "audio/mp4",
        "webm": "audio/webm",
        "ogg": "audio/ogg",
        "oga": "audio/ogg",
    }
    return by_ext.get(ext, mime or "application/octet-stream")


def _maybe_convert_ogg(data: bytes, mime: str, filename: str) -> tuple[bytes, str, str]:
    """Converte OGG para MP3 via ffmpeg quando disponível."""
    if mime not in ("audio/ogg", "application/ogg"):
        return data, mime, filename
    try:
        from app.media.assemble import ffmpeg_available
    except Exception:  # noqa: BLE001
        return data, mime, filename
    if not ffmpeg_available():
        return data, mime, filename
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "in.ogg"
        dst = Path(tmp) / "out.mp3"
        src.write_bytes(data)
        proc = subprocess.run(
            ["ffmpeg", "-y", "-i", str(src), "-vn", "-acodec", "libmp3lame", "-q:a", "4", str(dst)],
            capture_output=True,
        )
        if proc.returncode != 0 or not dst.is_file():
            return data, mime, filename
        return dst.read_bytes(), "audio/mpeg", Path(filename).stem + ".mp3"


def _clear_defaults(db: Session, user_id: uuid.UUID, except_id: uuid.UUID | None = None) -> None:
    voices = db.scalars(select(UserVoice).where(UserVoice.user_id == user_id)).all()
    for v in voices:
        if except_id and v.id == except_id:
            continue
        if v.is_default:
            v.is_default = False


@router.get("", response_model=VoiceListOut)
def list_voices(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VoiceListOut:
    rows = db.scalars(
        select(UserVoice).where(UserVoice.user_id == user.id).order_by(UserVoice.created_at.desc())
    ).all()
    return VoiceListOut(
        items=[_voice_out(v) for v in rows],
        custom_voice_available=elevenlabs_configured(),
    )


@router.post("", response_model=VoiceOut, status_code=status.HTTP_201_CREATED)
async def upload_voice(
    name: str = Form(...),
    file: UploadFile = File(...),
    make_default: str = Form(default="false"),
    user: User = Depends(require_registered_user),
    db: Session = Depends(get_db),
) -> VoiceOut:
    if not elevenlabs_configured():
        raise HTTPException(
            status_code=400,
            detail="Voz personalizada exige ELEVENLABS_API_KEY configurada no servidor",
        )
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Arquivo de audio vazio")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="Audio muito grande (max 10 MB)")
    mime = _guess_mime(file.filename, file.content_type)
    if mime not in ALLOWED_MIME:
        raise HTTPException(
            status_code=400,
            detail="Formato nao suportado. Use MP3, WAV, M4A, WEBM ou OGG",
        )
    data, mime, filename = _maybe_convert_ogg(data, mime, file.filename or "sample.mp3")
    ext = EXT_BY_MIME.get(mime, "mp3")
    display_name = (name or "").strip()[:120] or "Minha voz"
    try:
        el_voice_id = await clone_voice(display_name, data, filename, mime_type=mime)
    except TtsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    key = f"users/{user.id}/voices/{uuid.uuid4().hex}.{ext}"
    try:
        storage.put_bytes(key, data, mime)
    except storage.StorageNotConfigured:
        # Em testes/dev sem storage, ainda permite clonar e persistir metadados.
        key = f"users/{user.id}/voices/{uuid.uuid4().hex}.{ext}"

    want_default = str(make_default).lower() in ("1", "true", "yes", "on")
    # Primeira voz vira default automaticamente
    existing = db.scalar(select(UserVoice).where(UserVoice.user_id == user.id).limit(1))
    is_default = want_default or existing is None

    if is_default:
        _clear_defaults(db, user.id)

    voice = UserVoice(
        user_id=user.id,
        name=display_name,
        elevenlabs_voice_id=el_voice_id,
        sample_storage_key=key,
        mime_type=mime,
        is_default=is_default,
    )
    db.add(voice)
    db.commit()
    db.refresh(voice)
    return _voice_out(voice)


@router.patch("/{voice_id}", response_model=VoiceOut)
def patch_voice(
    voice_id: uuid.UUID,
    body: VoicePatchIn,
    user: User = Depends(require_registered_user),
    db: Session = Depends(get_db),
) -> VoiceOut:
    voice = db.get(UserVoice, voice_id)
    if voice is None or voice.user_id != user.id:
        raise HTTPException(status_code=404, detail="Voz nao encontrada")
    if body.name is not None:
        voice.name = body.name.strip()[:120] or voice.name
    if body.is_default is True:
        _clear_defaults(db, user.id, except_id=voice.id)
        voice.is_default = True
    elif body.is_default is False:
        voice.is_default = False
    db.commit()
    db.refresh(voice)
    return _voice_out(voice)


@router.delete("/{voice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_voice(
    voice_id: uuid.UUID,
    user: User = Depends(require_registered_user),
    db: Session = Depends(get_db),
) -> None:
    voice = db.get(UserVoice, voice_id)
    if voice is None or voice.user_id != user.id:
        raise HTTPException(status_code=404, detail="Voz nao encontrada")
    await delete_cloned_voice(voice.elevenlabs_voice_id)
    db.delete(voice)
    db.commit()
