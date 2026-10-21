"""História pelo GPT, sem chamar a API real."""

from __future__ import annotations

import pytest

from app.ai_clients import text_openai as gpt
from app.ai_clients.base import ProviderError
from app.ai_clients.factory import get_text_provider


class _FakeResponse:
    def __init__(self, status_code: int, json_data: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text or f"status {status_code}"

    def json(self):
        return self._json


class _FakeAsyncClient:
    calls: list[dict] = []
    script: list = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, **kwargs):
        _FakeAsyncClient.calls.append({"url": url, **kwargs})
        item = _FakeAsyncClient.script[len(_FakeAsyncClient.calls) - 1]
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    _FakeAsyncClient.calls = []
    _FakeAsyncClient.script = []
    monkeypatch.setattr(gpt.httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(gpt.settings, "openai_api_key", "test-key")
    monkeypatch.setattr(gpt.settings, "openai_text_model", "gpt-4.1")


def _chat(text: str) -> _FakeResponse:
    return _FakeResponse(
        200,
        {
            "choices": [{"message": {"content": text}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        },
    )


@pytest.mark.asyncio
async def test_generate_story_uses_chat_completions():
    _FakeAsyncClient.script = [_chat("Título: Ana e o Mar\nPágina 1: O mar chamou.")]
    provider = gpt.OpenAITextProvider()
    result = await provider.generate_story(
        brief="Ana gosta do mar", style="aquarela", pages=1, language="pt-BR", age=5
    )
    assert result.text.startswith("Título:")
    assert result.meta["model"] == "gpt-4.1"
    call = _FakeAsyncClient.calls[0]
    assert call["url"].endswith("/chat/completions")
    body = call["json"]
    assert body["model"] == "gpt-4.1"
    assert body["messages"][0]["role"] == "system"
    assert "Ana gosta do mar" in body["messages"][1]["content"]
    assert "response_format" not in body


@pytest.mark.asyncio
async def test_storyboard_asks_for_json():
    _FakeAsyncClient.script = [_chat('{"title":"Ana","scenes":[]}')]
    provider = gpt.OpenAITextProvider()
    await provider.generate_storyboard(story="Página 1: oi", theme="mar", title="Ana")
    assert _FakeAsyncClient.calls[0]["json"]["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_summarize_pages_splits_lines():
    _FakeAsyncClient.script = [_chat("O mar chamou.\nAna sorriu.")]
    lines = await gpt.OpenAITextProvider().summarize_pages(
        pages=["trecho 1", "trecho 2"], language="pt-BR"
    )
    assert lines == ["O mar chamou.", "Ana sorriu."]


@pytest.mark.asyncio
async def test_missing_key_and_transient_status(monkeypatch):
    monkeypatch.setattr(gpt.settings, "openai_api_key", None)
    provider = gpt.OpenAITextProvider(api_key="")
    with pytest.raises(ProviderError, match="OPENAI_API_KEY"):
        await provider.generate_story(brief="x", style="s", pages=1)
    monkeypatch.setattr(gpt.settings, "openai_api_key", "test-key")
    _FakeAsyncClient.script = [_FakeResponse(429, text="slow")]
    with pytest.raises(ProviderError, match="429") as exc:
        await gpt.OpenAITextProvider().generate_story(brief="x", style="s", pages=1)
    assert exc.value.transient is True


def test_factory_defaults_story_to_gpt(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "text_provider", "openai")
    provider = get_text_provider()
    assert provider.name == "openai"
    assert get_text_provider("gpt").name == "openai"
    assert get_text_provider("claude").name == "claude"
