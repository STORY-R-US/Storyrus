"""TextProvider: história, roteiro e legendas via GPT (Chat Completions)."""

from __future__ import annotations

import httpx

from app.ai_clients.base import ProviderError, TextResult
from app.ai_clients.text_anthropic import caption_messages, story_messages, storyboard_messages
from app.config import settings
from app.services.pricing import openai_text_cost

_API_URL = "https://api.openai.com/v1/chat/completions"
_TRANSIENT = frozenset({429, 500, 502, 503, 504})


def _message_text(data: dict) -> str:
    choices = data.get("choices") or []
    if not choices:
        return ""
    message = (choices[0] or {}).get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part) for part in content
        )
    return str(content or "")


class OpenAITextProvider:
    name = "openai"

    def __init__(
        self, api_key: str | None = None, timeout: float | None = None, model: str | None = None
    ):
        self._api_key = api_key or settings.openai_api_key
        self._timeout = settings.openai_timeout_s if timeout is None else timeout
        self._model = model or settings.openai_text_model
        self.last_cost_usd: float | None = None

    async def _complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int,
        json_object: bool = False,
    ) -> TextResult:
        if not (self._api_key or "").strip():
            raise ProviderError("OPENAI_API_KEY ausente", transient=False)
        payload: dict = {
            "model": self._model,
            "max_completion_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_object:
            payload["response_format"] = {"type": "json_object"}
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "content-type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(_API_URL, json=payload, headers=headers)
        except httpx.RequestError as exc:
            raise ProviderError(f"Falha de rede: {exc}", transient=True) from exc
        if resp.status_code in _TRANSIENT:
            raise ProviderError(
                f"OpenAI {resp.status_code}", transient=True, status_code=resp.status_code
            )
        if resp.status_code >= 400:
            raise ProviderError(
                f"OpenAI {resp.status_code}: {resp.text[:300]}",
                transient=False,
                status_code=resp.status_code,
            )
        data = resp.json()
        usage = data.get("usage") or {}
        cost = openai_text_cost(usage)
        self.last_cost_usd = cost
        return TextResult(
            text=_message_text(data),
            cost_usd=cost,
            meta={"usage": usage, "model": self._model, "provider": "openai"},
        )

    async def generate_story(
        self,
        *,
        brief: str,
        style: str,
        pages: int,
        language: str = "pt-BR",
        age: int | None = None,
    ) -> TextResult:
        system, user = story_messages(
            brief=brief, style=style, pages=pages, language=language, age=age
        )
        return await self._complete(system=system, user=user, max_tokens=4000)

    async def generate_storyboard(
        self, *, story: str, theme: str, title: str = "", language: str = "pt-BR"
    ) -> TextResult:
        system, user = storyboard_messages(story=story, theme=theme, title=title, language=language)
        return await self._complete(system=system, user=user, max_tokens=8000, json_object=True)

    async def summarize_pages(
        self, *, pages: list[str], style: str = "", language: str = "pt-BR"
    ) -> list[str]:
        if not pages:
            return []
        system, user = caption_messages(pages=pages, language=language)
        result = await self._complete(system=system, user=user, max_tokens=1500)
        return [ln.strip(" -•\t").strip() for ln in result.text.splitlines() if ln.strip()]
