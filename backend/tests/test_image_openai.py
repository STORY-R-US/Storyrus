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
async def test_editorial_reframe_masks_only_added_top_and_attaches_original_photos():
    edited = io.BytesIO()
    # Simulate an editor that changes EVERY pixel, ignoring its protected mask.
    Image.new("RGB", (100, 100), "red").save(edited, "PNG")
    _FakeAsyncClient.script = [_FakeResponse(200, _ok_payload(edited.getvalue()))]
    raw = io.BytesIO()
    original = Image.new("RGB", (100, 100), "blue")
    original.putpixel((20, 30), (17, 45, 91))
    original.save(raw, "PNG")
    provider = oai.OpenAIImageProvider()
    result = await provider.reframe_editorial_art(
        art=raw.getvalue(), photos=[raw.getvalue()], top_fraction=0.2, prompt="keep identity"
    )
    output = Image.open(io.BytesIO(result.image_bytes)).convert("RGB")
    assert output.getpixel((20, 10)) == (255, 0, 0)  # generated background retained
    assert output.getpixel((20, 50)) == (17, 45, 91)  # shifted subject preserved
    assert output.crop((0, 20, 100, 100)).tobytes() == original.crop((0, 0, 100, 80)).tobytes()
    assert result.meta["protected_source_pixels"] is True
    request = _FakeAsyncClient.calls[0]
    assert request["data"]["input_fidelity"] == "high"
    files = request["files"]
    assert [part[0] for part in files] == ["image[]", "mask", "image[]"]
    canvas = Image.open(io.BytesIO(files[0][1][1]))
    mask = Image.open(io.BytesIO(files[1][1][1]))
    assert canvas.size == mask.size == original.size
    assert canvas.getpixel((20, 50))[:3] == (17, 45, 91)  # moved; never scaled
    assert canvas.getpixel((20, 10))[3] == mask.getpixel((20, 10))[3] == 0
    assert mask.getpixel((20, 50))[3] == 255
    assert Image.open(io.BytesIO(files[2][1][1])).getpixel((20, 30)) == (17, 45, 91)


@pytest.mark.asyncio
async def test_complete_scene_reframe_preserves_all_source_edges_and_activity():
    edited = io.BytesIO()
    Image.new("RGB", (100, 100), "red").save(edited, "PNG")
    _FakeAsyncClient.script = [_FakeResponse(200, _ok_payload(edited.getvalue()))]
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
    assert output.getpixel((0, 80)) == output.getpixel((50, 0)) == (255, 0, 0)
    mask = Image.open(io.BytesIO(_FakeAsyncClient.calls[0]["files"][1][1][1]))
    assert mask.getpixel((0, 80))[3] == mask.getpixel((50, 0))[3] == 0
    assert mask.getpixel((50, 80))[3] == 255


@pytest.mark.asyncio
async def test_complete_scene_reframe_allows_full_catalog_reserve_clearance():
    edited = io.BytesIO()
    Image.new("RGB", (100, 100), "red").save(edited, "PNG")
    _FakeAsyncClient.script = [_FakeResponse(200, _ok_payload(edited.getvalue()))]
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
    with pytest.raises(ValueError, match="Enquadramento editorial inválido"):
        await oai.OpenAIImageProvider().reframe_editorial_art(
            art=original.getvalue(),
            photos=[],
            top_fraction=oai.MAX_REFRAME_TOP_FRACTION + 0.01,
            prompt="quiet scenery",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_image", [True, False])
async def test_editorial_reframe_rejects_invalid_or_wrong_size_response(invalid_image):
    original = io.BytesIO()
    Image.new("RGB", (100, 100), "blue").save(original, "PNG")
    edited = io.BytesIO()
    Image.new("RGB", (50, 50), "red").save(edited, "PNG")
    payload = b"invalid" if invalid_image else edited.getvalue()
    _FakeAsyncClient.script = [_FakeResponse(200, _ok_payload(payload))]
    with pytest.raises(ProviderError):
        await oai.OpenAIImageProvider().reframe_editorial_art(
            art=original.getvalue(), photos=[], top_fraction=0.2, prompt="preserve identity"
        )


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
