"""OpenAI GPT Image provider (sem API real)."""

from __future__ import annotations

import base64

import pytest

from app.ai_clients import image_openai as oai
from app.ai_clients.base import ProviderError


def _ok_payload(image: bytes = b"png-bytes") -> dict:
    return {
        "data": [{"b64_json": base64.b64encode(image).decode()}],
        "usage": {},
    }


class _FakeResponse:
    def __init__(self, status_code: int, json_data: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text or f"status {status_code}"
        self.headers = {}

    def json(self):
        return self._json


class _FakeAsyncClient:
    script: list = []
    calls: list[dict] = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, **kwargs):
        _FakeAsyncClient.calls.append({"url": url, **kwargs})
        idx = len(_FakeAsyncClient.calls) - 1
        item = (
            _FakeAsyncClient.script[idx]
            if idx < len(_FakeAsyncClient.script)
            else _FakeAsyncClient.script[-1]
        )
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    _FakeAsyncClient.script = []
    _FakeAsyncClient.calls = []
    monkeypatch.setattr(oai.httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(oai.settings, "openai_api_key", "test-key")
    monkeypatch.setattr(oai.settings, "openai_image_model", "gpt-image-1")
    monkeypatch.setattr(oai.settings, "openai_image_quality", "high")
    monkeypatch.setattr(oai.settings, "openai_max_retries", 2)
    monkeypatch.setattr(oai.settings, "openai_retry_base_s", 0.0)
    monkeypatch.setattr(oai.settings, "openai_retry_max_s", 0.0)

    async def _noop_sleep(*_a, **_k):
        return None

    monkeypatch.setattr(oai.asyncio, "sleep", _noop_sleep)
    yield


@pytest.mark.asyncio
async def test_generate_character_uses_generations_when_no_refs():
    _FakeAsyncClient.script = [_FakeResponse(200, _ok_payload(b"char"))]
    provider = oai.OpenAIImageProvider()
    result = await provider.generate_character(prompt="hero", reference_images=[], style="cgi")
    assert result.image_bytes == b"char"
    assert result.cost_usd == oai.settings.price_openai_image_usd
    assert "/images/generations" in _FakeAsyncClient.calls[0]["url"]


@pytest.mark.asyncio
async def test_generate_scene_uses_edits_with_avatar():
    _FakeAsyncClient.script = [_FakeResponse(200, _ok_payload(b"scene"))]
    provider = oai.OpenAIImageProvider()
    result = await provider.generate_scene(
        prompt="forest",
        character_ref=b"avatar",
        style="cgi",
    )
    assert result.image_bytes == b"scene"
    call = _FakeAsyncClient.calls[0]
    assert "/images/edits" in call["url"]
    assert call.get("files")
    assert call["data"]["input_fidelity"] == "high"
    assert call["data"]["quality"] == "high"


@pytest.mark.asyncio
async def test_scene_and_reading_receive_original_photo_before_generated_reference():
    _FakeAsyncClient.script = [_FakeResponse(200, _ok_payload())]
    provider = oai.OpenAIImageProvider()
    await provider.generate_scene(
        prompt="Same child reading the approved book",
        character_ref=b"cover",
        photo=b"original-photo",
        extra_refs=[b"pet-photo"],
        style="cartoon",
        reference_role="cover",
    )
    call = _FakeAsyncClient.calls[0]
    assert [value[1] for _, value in call["files"]] == [b"original-photo", b"cover", b"pet-photo"]
    assert "FOTO ORIGINAL" in call["data"]["prompt"]
    assert "unica fonte de verdade do rosto" not in call["data"]["prompt"]


@pytest.mark.asyncio
async def test_product_photo_preserves_cover_prompt_and_reference_role():
    _FakeAsyncClient.script = [_FakeResponse(200, _ok_payload(b"product"))]
    provider = oai.OpenAIImageProvider()
    await provider.generate_scene(
        prompt="A PRIMEIRA imagem é a CAPA. Use esta capa no livro físico.",
        character_ref=b"cover",
        reference_role="cover",
        style="photoreal product photo",
    )
    prompt = _FakeAsyncClient.calls[0]["data"]["prompt"]
    assert prompt.startswith("A PRIMEIRA imagem é a CAPA.")
    assert "AVATAR" not in prompt
    assert "Ilustre" not in prompt


@pytest.mark.asyncio
async def test_multiple_reference_files_use_matching_mime_types():
    _FakeAsyncClient.script = [_FakeResponse(200, _ok_payload())]
    await oai.OpenAIImageProvider().generate_character(
        prompt="saved prompt",
        reference_images=[b"\xff\xd8\xffPHOTO", b"\x89PNG\r\n\x1a\nIMAGE"],
        style="cartoon",
    )
    files = _FakeAsyncClient.calls[0]["files"]
    assert [field for field, _ in files] == ["image[]", "image[]"]
    assert [value[2] for _, value in files] == ["image/jpeg", "image/png"]


@pytest.mark.asyncio
async def test_refine_identity_uses_edits():
    _FakeAsyncClient.script = [_FakeResponse(200, _ok_payload(b"refined"))]
    provider = oai.OpenAIImageProvider()
    result = await provider.refine_identity(photo=b"p", illustration=b"ill", style="CGI 3D")
    assert result.image_bytes == b"refined"
    call = _FakeAsyncClient.calls[0]
    assert "/images/edits" in call["url"]
    assert call.get("files")
    assert len(call["files"]) == 2


@pytest.mark.asyncio
async def test_refine_scene_uses_edits():
    _FakeAsyncClient.script = [_FakeResponse(200, _ok_payload(b"scene-r"))]
    provider = oai.OpenAIImageProvider()
    result = await provider.refine_scene(character_ref=b"avatar", scene=b"scene", style="cgi")
    assert result.image_bytes == b"scene-r"
    call = _FakeAsyncClient.calls[0]
    assert "/images/edits" in call["url"]
    assert len(call["files"]) == 2


@pytest.mark.asyncio
async def test_transient_503_retries_then_ok():
    _FakeAsyncClient.script = [
        _FakeResponse(503, text="busy"),
        _FakeResponse(200, _ok_payload(b"ok")),
    ]
    provider = oai.OpenAIImageProvider()
    result = await provider.generate_character(prompt="x", reference_images=[], style="s")
    assert result.image_bytes == b"ok"
    assert len(_FakeAsyncClient.calls) == 2


@pytest.mark.asyncio
async def test_missing_api_key_raises(monkeypatch):
    monkeypatch.setattr(oai.settings, "openai_api_key", None)
    provider = oai.OpenAIImageProvider(api_key="")
    with pytest.raises(ProviderError, match="OPENAI_API_KEY"):
        await provider.generate_character(prompt="x", reference_images=[], style="s")


def test_factory_registers_openai():
    from app.ai_clients.factory import get_image_provider

    provider = get_image_provider("openai")
    assert provider.name == "openai"


@pytest.mark.asyncio
async def test_rehearsal_returns_generic_image_without_calling_openai(monkeypatch):
    monkeypatch.setattr(oai.settings, "skip_openai", True)
    _FakeAsyncClient.calls.clear()
    provider = oai.OpenAIImageProvider(api_key="nao-usar")
    result = await provider.generate_character(prompt="capa", reference_images=[], style="s")
    assert result.meta["provider"] == "demo"
    assert result.meta["rehearsal"] is True
    assert result.cost_usd == 0
    assert result.image_bytes.startswith(b"\x89PNG")
    assert _FakeAsyncClient.calls == []
