"""TextProvider OpenAI (sem API real)."""

from __future__ import annotations

import pytest

from app.ai_clients import text_openai as oai
from app.ai_clients.base import ProviderError
from app.ai_clients.factory import get_text_provider


def _ok(text: str = "Título: Luna\nPágina 1: Era uma vez.") -> dict:
    return {
        "choices": [{"message": {"content": text}}],
        "usage": {"prompt_tokens": 1000, "completion_tokens": 500},
    }


class _FakeResponse:
    def __init__(self, status_code: int, json_data: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text or f"status {status_code}"

    def json(self):
        return self._json


class _FakeAsyncClient:
    script: list = []
    calls: list[dict] = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, json=None, headers=None):
        self.calls.append({"url": url, "json": json, "headers": headers})
        status, payload = self.script.pop(0)
        return _FakeResponse(status, payload)


@pytest.fixture
def client(monkeypatch):
    _FakeAsyncClient.script = []
    _FakeAsyncClient.calls = []
    monkeypatch.setattr(oai.httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(oai.settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(oai.settings, "openai_text_model", "gpt-4.1")
    return _FakeAsyncClient


@pytest.mark.asyncio
async def test_generate_story_uses_chat_completions(client):
    client.script = [(200, _ok())]
    provider = oai.OpenAITextProvider()
    result = await provider.generate_story(brief="Luna e a floresta", style="cartoon", pages=1)
    call = client.calls[0]
    assert call["url"].endswith("/chat/completions")
    assert call["json"]["model"] == "gpt-4.1"
    assert call["headers"]["Authorization"] == "Bearer sk-test"
    assert call["json"]["messages"][0]["role"] == "system"
    assert "Luna e a floresta" in call["json"]["messages"][1]["content"]
    assert result.text.startswith("Título:")
    assert result.meta["provider"] == "openai"
    assert result.cost_usd > 0


@pytest.mark.asyncio
async def test_summarize_pages_splits_lines(client):
    client.script = [(200, _ok("A lua sorriu.\nO rio cantou."))]
    lines = await oai.OpenAITextProvider().summarize_pages(pages=["um", "dois"])
    assert lines == ["A lua sorriu.", "O rio cantou."]


@pytest.mark.asyncio
async def test_prepare_book_profile_sends_photo(client):
    client.script = [(200, _ok('{"title":"Luna"}'))]
    photo = b"\xff\xd8\xfffake"
    await oai.OpenAITextProvider().prepare_book_profile(ficha={"name": "Luna"}, photos=[photo])
    parts = client.calls[0]["json"]["messages"][1]["content"]
    assert parts[0]["type"] == "image_url"
    assert parts[0]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert parts[1]["type"] == "text"


@pytest.mark.asyncio
async def test_missing_key_and_transient_error(client, monkeypatch):
    monkeypatch.setattr(oai.settings, "openai_api_key", None)
    with pytest.raises(ProviderError, match="OPENAI_API_KEY"):
        await oai.OpenAITextProvider(api_key="").generate_story(brief="x", style="s", pages=1)

    monkeypatch.setattr(oai.settings, "openai_api_key", "sk-test")
    client.script = [(429, {"error": "slow"})]
    with pytest.raises(ProviderError, match="429") as exc:
        await oai.OpenAITextProvider().generate_story(brief="x", style="s", pages=1)
    assert exc.value.transient is True


def test_factory_text_provider_is_openai():
    assert get_text_provider("openai").name == "openai"
    assert get_text_provider("claude").name == "openai"
