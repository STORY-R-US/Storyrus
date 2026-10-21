"""VideoProvider real: Kling (image2video).

Autenticacao:
  - Novo (preferido): ``KLING_API_KEY`` → Bearer direto em
    ``https://api-singapore.klingai.com`` (path com modelo).
  - Legado: ``KLING_ACCESS_KEY`` + ``KLING_SECRET_KEY`` → JWT HS256 em
    ``/v1/videos/image2video`` (``model_name`` no body).

Fluxo task-based: cria a tarefa e consulta o resultado (polling/callback).
"""

from __future__ import annotations

import base64
import time

import httpx
from jose import jwt

from app.ai_clients.base import ProviderError, VideoJob
from app.config import settings
from app.services.pricing import video_cost

_BASE_NEW = "https://api-singapore.klingai.com"
_BASE_LEGACY = "https://api-singapore.klingai.com"
_MODEL_NEW = "kling-2.6"
_MODEL_LEGACY = "kling-v2"
_CREATE_NEW = f"/image-to-video/{_MODEL_NEW}"
_CREATE_LEGACY = "/v1/videos/image2video"
_TASKS = "/tasks"


def _make_token(access_key: str, secret_key: str) -> str:
    now = int(time.time())
    payload = {"iss": access_key, "exp": now + 1800, "nbf": now - 5}
    return jwt.encode(
        payload, secret_key, algorithm="HS256", headers={"alg": "HS256", "typ": "JWT"}
    )


def _map_status(s: str) -> str:
    return {
        "submitted": "PENDING",
        "processing": "RUNNING",
        "succeed": "DONE",  # legado
        "succeeded": "DONE",  # API nova
        "failed": "FAILED",
    }.get((s or "").lower(), "RUNNING")


def _b64_image(image: bytes) -> str:
    return base64.b64encode(image).decode()


def _clamp_duration(duration_s: int) -> int:
    return 10 if int(duration_s) >= 8 else 5


class KlingVideoProvider:
    name = "kling"

    def __init__(
        self,
        api_key: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        timeout: float = 60.0,
    ):
        self._api_key = api_key if api_key is not None else settings.kling_api_key
        self._ak = access_key if access_key is not None else settings.kling_access_key
        self._sk = secret_key if secret_key is not None else settings.kling_secret_key
        self._timeout = timeout

    @property
    def uses_api_key(self) -> bool:
        return bool(self._api_key)

    def _headers(self) -> dict:
        if self._api_key:
            token = self._api_key
        elif self._ak and self._sk:
            token = _make_token(self._ak, self._sk)
        else:
            raise ProviderError(
                "KLING_API_KEY (ou KLING_ACCESS_KEY/SECRET_KEY) ausente",
                transient=False,
            )
        return {
            "Authorization": f"Bearer {token}",
            "content-type": "application/json",
        }

    @staticmethod
    def _check(resp: httpx.Response) -> dict | list:
        if resp.status_code in (429, 500, 502, 503, 504):
            raise ProviderError(
                f"Kling {resp.status_code}", transient=True, status_code=resp.status_code
            )
        if resp.status_code >= 400:
            raise ProviderError(
                f"Kling {resp.status_code}: {resp.text[:300]}",
                transient=False,
                status_code=resp.status_code,
            )
        body = resp.json()
        if body.get("code", 0) != 0:
            raise ProviderError(f"Kling code={body.get('code')}: {body.get('message')}")
        return body.get("data", {})

    async def create_video(self, *, image: bytes, prompt: str, duration_s: int) -> VideoJob:
        billed_s = _clamp_duration(duration_s)
        if self.uses_api_key:
            return await self._create_new(image=image, prompt=prompt, duration_s=billed_s)
        return await self._create_legacy(image=image, prompt=prompt, duration_s=billed_s)

    async def poll_video(self, *, provider_task_id: str) -> VideoJob:
        if self.uses_api_key:
            return await self._poll_new(provider_task_id=provider_task_id)
        return await self._poll_legacy(provider_task_id=provider_task_id)

    async def _create_new(self, *, image: bytes, prompt: str, duration_s: int) -> VideoJob:
        payload = {
            "contents": [
                {"type": "prompt", "text": (prompt or "")[:2500]},
                {"type": "first_frame", "url": _b64_image(image)},
            ],
            "settings": {
                "audio": "off",
                "resolution": "720p",
                "duration": duration_s,
            },
            "options": {"watermark_info": {"enabled": False}},
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{_BASE_NEW}{_CREATE_NEW}", json=payload, headers=self._headers()
                )
        except httpx.RequestError as exc:
            raise ProviderError(f"Falha de rede: {exc}", transient=True) from exc

        data = self._check(resp)
        if not isinstance(data, dict):
            raise ProviderError("Kling: resposta de create inesperada")
        task_id = data.get("id") or data.get("task_id") or ""
        status = data.get("status") or data.get("task_status") or "submitted"
        return VideoJob(
            provider_task_id=str(task_id),
            status=_map_status(status),
            cost_usd=video_cost(duration_s),
            meta={"model": _MODEL_NEW, "duration_s": duration_s, "auth": "api_key"},
        )

    async def _poll_new(self, *, provider_task_id: str) -> VideoJob:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    f"{_BASE_NEW}{_TASKS}",
                    params={"task_ids": provider_task_id},
                    headers=self._headers(),
                )
        except httpx.RequestError as exc:
            raise ProviderError(f"Falha de rede: {exc}", transient=True) from exc

        data = self._check(resp)
        row: dict
        if isinstance(data, list):
            if not data:
                return VideoJob(provider_task_id=provider_task_id, status="RUNNING")
            row = data[0] if isinstance(data[0], dict) else {}
        elif isinstance(data, dict):
            # alguns envelopes envolvem em result
            result = data.get("result")
            if isinstance(result, list) and result:
                row = result[0] if isinstance(result[0], dict) else {}
            else:
                row = data
        else:
            row = {}

        status = _map_status(str(row.get("status") or row.get("task_status") or "processing"))
        video_url = None
        duration_s = None
        for out in row.get("outputs") or []:
            if isinstance(out, dict) and out.get("type") == "video" and out.get("url"):
                video_url = out["url"]
                duration_s = out.get("duration")
                break
        # fallback legado embutido
        if not video_url:
            videos = (row.get("task_result") or {}).get("videos") or []
            if videos:
                video_url = videos[0].get("url")
                duration_s = videos[0].get("duration")

        return VideoJob(
            provider_task_id=provider_task_id,
            status=status,
            video_url=video_url,
            cost_usd=video_cost(duration_s) if duration_s else None,
            meta={"model": _MODEL_NEW, "duration_s": duration_s, "auth": "api_key"},
        )

    async def _create_legacy(self, *, image: bytes, prompt: str, duration_s: int) -> VideoJob:
        payload = {
            "model_name": _MODEL_LEGACY,
            "image": _b64_image(image),
            "prompt": prompt,
            "duration": str(duration_s),
            "mode": "std",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{_BASE_LEGACY}{_CREATE_LEGACY}", json=payload, headers=self._headers()
                )
        except httpx.RequestError as exc:
            raise ProviderError(f"Falha de rede: {exc}", transient=True) from exc

        data = self._check(resp)
        if not isinstance(data, dict):
            raise ProviderError("Kling: resposta de create inesperada")
        return VideoJob(
            provider_task_id=data.get("task_id", ""),
            status=_map_status(data.get("task_status", "submitted")),
            cost_usd=video_cost(duration_s),
            meta={"model": _MODEL_LEGACY, "duration_s": duration_s, "auth": "jwt"},
        )

    async def _poll_legacy(self, *, provider_task_id: str) -> VideoJob:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    f"{_BASE_LEGACY}{_CREATE_LEGACY}/{provider_task_id}",
                    headers=self._headers(),
                )
        except httpx.RequestError as exc:
            raise ProviderError(f"Falha de rede: {exc}", transient=True) from exc

        data = self._check(resp)
        if not isinstance(data, dict):
            raise ProviderError("Kling: resposta de poll inesperada")
        status = _map_status(data.get("task_status", "processing"))
        video_url = None
        videos = (data.get("task_result") or {}).get("videos") or []
        if videos:
            video_url = videos[0].get("url")
        duration_s = data.get("duration") or (videos[0].get("duration") if videos else None)
        return VideoJob(
            provider_task_id=provider_task_id,
            status=status,
            video_url=video_url,
            cost_usd=video_cost(duration_s) if duration_s else None,
            meta={"model": _MODEL_LEGACY, "duration_s": duration_s, "auth": "jwt"},
        )
