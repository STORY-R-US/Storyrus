"""TTS providers for narrated video.

ElevenLabs when ELEVENLABS_API_KEY is set; otherwise edge-tts (PT-BR).
Also supports Instant Voice Clone (IVC) for custom reusable voices.
"""

from __future__ import annotations

from typing import Protocol

import httpx

from app.config import settings

# Voz padrão infantil/narrativa em português (edge-tts).
_EDGE_VOICE = "pt-BR-FranciscaNeural"
# Voz ElevenLabs padrão (Rachel) — sobrescrita por ELEVENLABS_VOICE_ID.
_DEFAULT_ELEVEN_VOICE = "21m00Tcm4TlvDq8ikWAM"

_ELEVEN_BASE = "https://api.elevenlabs.io/v1"


class TtsError(Exception):
    def __init__(self, message: str, *, transient: bool = False):
        super().__init__(message)
        self.transient = transient


class TtsProvider(Protocol):
    name: str

    async def synthesize(self, text: str, *, language: str = "pt-BR") -> bytes:
        """Retorna áudio MP3."""
        ...


class EdgeTtsProvider:
    name = "edge-tts"

    async def synthesize(self, text: str, *, language: str = "pt-BR") -> bytes:
        try:
            import edge_tts
        except ImportError as exc:
            raise TtsError("Pacote edge-tts nao instalado", transient=False) from exc

        voice = _EDGE_VOICE
        if (language or "").lower().startswith("en"):
            voice = "en-US-JennyNeural"
        communicate = edge_tts.Communicate((text or "").strip() or "...", voice)
        chunks: list[bytes] = []
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio":
                chunks.append(chunk["data"])
        if not chunks:
            raise TtsError("edge-tts nao retornou audio", transient=True)
        return b"".join(chunks)


class ElevenLabsTtsProvider:
    name = "elevenlabs"

    def __init__(self, api_key: str | None = None, voice_id: str | None = None):
        self._key = api_key or settings.elevenlabs_api_key
        self._voice = voice_id or settings.elevenlabs_voice_id or _DEFAULT_ELEVEN_VOICE

    async def synthesize(self, text: str, *, language: str = "pt-BR") -> bytes:
        if not self._key:
            raise TtsError("ELEVENLABS_API_KEY ausente", transient=False)
        url = f"{_ELEVEN_BASE}/text-to-speech/{self._voice}"
        payload = {
            "text": (text or "").strip() or "...",
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.75},
        }
        headers = {
            "xi-api-key": self._key,
            "accept": "audio/mpeg",
            "content-type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                resp = await client.post(url, json=payload, headers=headers)
        except httpx.RequestError as exc:
            raise TtsError(f"Falha de rede ElevenLabs: {exc}", transient=True) from exc
        if resp.status_code in (429, 500, 502, 503, 504):
            raise TtsError(f"ElevenLabs {resp.status_code}", transient=True)
        if resp.status_code >= 400:
            raise TtsError(f"ElevenLabs {resp.status_code}: {resp.text[:300]}", transient=False)
        return resp.content


def elevenlabs_configured() -> bool:
    return bool(settings.elevenlabs_api_key)


def get_tts_provider(voice_id: str | None = None) -> TtsProvider:
    """Retorna provider TTS. Com voice_id custom exige ElevenLabs."""
    if settings.elevenlabs_api_key:
        return ElevenLabsTtsProvider(voice_id=voice_id)
    return EdgeTtsProvider()


def _friendly_clone_error(status: int, body: str) -> str:
    lower = (body or "").lower()
    if status == 401:
        return "Chave ElevenLabs invalida ou ausente"
    if status == 402 or "quota" in lower or "credit" in lower:
        return "Cota ElevenLabs insuficiente para clonar voz"
    if "duration" in lower or "too short" in lower or "short" in lower:
        return "Audio muito curto. Grave 30 a 60 segundos de fala clara, sem musica de fundo."
    if "too long" in lower:
        return "Audio muito longo. Use um trecho de ate cerca de 1 minuto."
    if status == 422 or "invalid" in lower or "corrupt" in lower:
        return "Nao foi possivel clonar esta amostra. Use MP3/WAV/M4A com fala clara."
    return f"Falha ao clonar voz (ElevenLabs {status}): {body[:200]}"


async def clone_voice(
    name: str,
    audio_bytes: bytes,
    filename: str,
    *,
    mime_type: str = "audio/mpeg",
) -> str:
    """Instant Voice Clone. Retorna elevenlabs_voice_id."""
    if not settings.elevenlabs_api_key:
        raise TtsError(
            "Voz personalizada exige ELEVENLABS_API_KEY configurada",
            transient=False,
        )
    headers = {"xi-api-key": settings.elevenlabs_api_key}
    files = {"files": (filename or "sample.mp3", audio_bytes, mime_type or "audio/mpeg")}
    data = {
        "name": (name or "Voz personalizada").strip()[:100] or "Voz personalizada",
        "description": "StoryRUs custom narrator voice",
    }
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{_ELEVEN_BASE}/voices/add",
                headers=headers,
                data=data,
                files=files,
            )
    except httpx.RequestError as exc:
        raise TtsError(f"Falha de rede ElevenLabs: {exc}", transient=True) from exc
    if resp.status_code in (429, 500, 502, 503, 504):
        raise TtsError(_friendly_clone_error(resp.status_code, resp.text), transient=True)
    if resp.status_code >= 400:
        raise TtsError(_friendly_clone_error(resp.status_code, resp.text), transient=False)
    try:
        voice_id = (resp.json() or {}).get("voice_id")
    except Exception as exc:
        raise TtsError("Resposta invalida do ElevenLabs ao clonar voz", transient=False) from exc
    if not voice_id:
        raise TtsError("ElevenLabs nao retornou voice_id", transient=False)
    return str(voice_id)


async def delete_cloned_voice(voice_id: str) -> None:
    """Remove voz clonada no ElevenLabs (best-effort)."""
    if not settings.elevenlabs_api_key or not voice_id:
        return
    headers = {"xi-api-key": settings.elevenlabs_api_key}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            await client.delete(f"{_ELEVEN_BASE}/voices/{voice_id}", headers=headers)
    except httpx.RequestError:
        pass
