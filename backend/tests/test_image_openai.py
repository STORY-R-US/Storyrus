"""OpenAI GPT Image provider (sem API real)."""

from __future__ import annotations

import base64
import io

import pytest
from PIL import Image

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
async def test_editorial_reframe_uses_local_background_and_preserves_source_pixels():
    raw = io.BytesIO()
    original = Image.new("RGB", (100, 100), "blue")
    original.putpixel((20, 30), (17, 45, 91))
    original.save(raw, "PNG")
    provider = oai.OpenAIImageProvider()
    result = await provider.reframe_editorial_art(
        art=raw.getvalue(), photos=[raw.getvalue()], top_fraction=0.2, prompt="keep identity"
    )
    output = Image.open(io.BytesIO(result.image_bytes)).convert("RGB")
    assert output.getpixel((50, 10)) == (0, 0, 255)  # scene-matched, subject-free reserve
    assert output.getpixel((20, 50)) == (17, 45, 91)  # shifted subject preserved
    assert output.crop((0, 20, 100, 100)).tobytes() == original.crop((0, 0, 100, 80)).tobytes()
    assert result.meta["protected_source_pixels"] is True
    assert result.cost_usd == 0
    assert result.meta["provider"] == "local"
    assert result.meta["billable"] is False
    assert _FakeAsyncClient.calls == []


@pytest.mark.asyncio
async def test_complete_scene_reframe_preserves_all_source_edges_and_activity():
    original = Image.new("RGB", (100, 100), "blue")
    original.paste("green", (0, 90, 100, 100))
    raw = io.BytesIO()
    original.save(raw, "PNG")
    result = await oai.OpenAIImageProvider().reframe_editorial_art(
        art=raw.getvalue(),
        photos=[],
        top_fraction=0.3,
        prompt="quiet scenery",
        preserve_complete_scene=True,
    )
    output = Image.open(io.BytesIO(result.image_bytes)).convert("RGB")
    assert (
        output.crop((15, 30, 85, 100)).tobytes()
        == original.resize((70, 70), Image.Resampling.LANCZOS).tobytes()
    )
    assert output.getpixel((50, 99)) == (0, 128, 0)
    assert output.getpixel((0, 80)) == output.getpixel((50, 0)) == (0, 0, 255)
    assert result.cost_usd == 0
    assert _FakeAsyncClient.calls == []


@pytest.mark.asyncio
async def test_local_reframe_keeps_subject_out_of_measured_title_reserve():
    raw = io.BytesIO()
    original = Image.new("RGB", (100, 100), "blue")
    for y in range(0, 36):
        for x in range(25, 76):
            original.putpixel((x, y), (220, 20, 30))
    original.save(raw, "PNG")

    result = await oai.OpenAIImageProvider().reframe_editorial_art(
        art=raw.getvalue(),
        photos=[raw.getvalue()],
        top_fraction=0.4,
        clear_through_fraction=0.34,
        prompt="background only",
        preserve_complete_scene=True,
    )

    output = Image.open(io.BytesIO(result.image_bytes)).convert("RGB")
    assert all(output.getpixel((x, y)) != (220, 20, 30) for x in range(9, 92) for y in range(6, 35))
    assert result.meta["clear_through_fraction"] == 0.34
    assert _FakeAsyncClient.calls == []


@pytest.mark.asyncio
async def test_complete_scene_reframe_allows_full_catalog_reserve_clearance():
    original = io.BytesIO()
    Image.new("RGB", (100, 100), "blue").save(original, "PNG")
    result = await oai.OpenAIImageProvider().reframe_editorial_art(
        art=original.getvalue(),
        photos=[],
        top_fraction=oai.MAX_REFRAME_TOP_FRACTION,
        prompt="quiet scenery",
        preserve_complete_scene=True,
    )
    assert result.meta["generated_top_fraction"] == oai.MAX_REFRAME_TOP_FRACTION
    assert result.cost_usd == 0
    assert _FakeAsyncClient.calls == []
    with pytest.raises(ValueError, match="Enquadramento editorial inválido"):
        await oai.OpenAIImageProvider().reframe_editorial_art(
            art=original.getvalue(),
            photos=[],
            top_fraction=oai.MAX_REFRAME_TOP_FRACTION + 0.01,
            prompt="quiet scenery",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("art,top_fraction", [(b"invalid", 0.2), (b"", 0.2)])
async def test_editorial_reframe_rejects_invalid_source_image(art, top_fraction):
    with pytest.raises(OSError):
        await oai.OpenAIImageProvider().reframe_editorial_art(
            art=art, photos=[], top_fraction=top_fraction, prompt="preserve identity"
        )
    assert _FakeAsyncClient.calls == []


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


def test_moderation_error_keeps_code_details_and_request_id():
    response = _FakeResponse(
        400,
        json_data={
            "error": {
                "message": "The request was rejected by the safety system.",
                "type": "image_generation_user_error",
                "param": None,
                "code": "moderation_blocked",
                "moderation_details": {"stage": "input"},
            }
        },
    )
    response.headers["x-request-id"] = "req_abc123"

    error = oai._error_from_response(response)

    assert error.status_code == 400
    assert error.transient is False
    assert '"code":"moderation_blocked"' in str(error)
    assert '"moderation_details":{"stage":"input"}' in str(error)
    assert '"request_id":"req_abc123"' in str(error)


def test_error_body_without_json_keeps_short_text_fallback():
    response = _FakeResponse(400, text="plain error")

    error = oai._error_from_response(response)

    assert "OpenAI 400: plain error" == str(error)


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
