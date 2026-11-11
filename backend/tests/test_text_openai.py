"""TextProvider OpenAI (sem API real)."""

from __future__ import annotations

import base64
import io
import json

import httpx
import pytest
from PIL import Image

from app.ai_clients import text_openai as oai
from app.ai_clients.base import ProviderError
from app.ai_clients.factory import get_text_provider


def _ok(text: str = "Título: Luna\nPágina 1: Era uma vez.") -> dict:
    return {
        "choices": [{"message": {"content": text}}],
        "usage": {"prompt_tokens": 1000, "completion_tokens": 500},
    }


@pytest.mark.asyncio
async def test_editorial_review_separates_output_from_references_and_crops_measured_region(client):
    client.script = [(200, _ok('{"valid":true,"issues":[],"limitations":[]}'))] * 2
    raw = io.BytesIO()
    Image.new("RGB", (100, 100), "blue").save(raw, "PNG")
    await oai.OpenAITextProvider().validate_editorial_preview(
        data=raw.getvalue(),
        photos=[b"original"],
        cover=None,
        prompt="ARTE_BASE",
        style_refs=[b"style"],
        inspection_region=[0.25, 0.05, 0.75, 0.25],
    )
    crop_content = client.calls[0]["json"]["messages"][1]["content"]
    crop_images = [part["image_url"] for part in crop_content if part["type"] == "image_url"]
    assert len(crop_images) == 1
    crop_bytes = base64.b64decode(crop_images[0]["url"].split(",")[1])
    assert Image.open(io.BytesIO(crop_bytes)).size == (50, 20)
    content = client.calls[1]["json"]["messages"][1]["content"]
    images = [part["image_url"] for part in content if part["type"] == "image_url"]
    decoded = [base64.b64decode(part["url"].split(",")[1]) for part in images]
    assert decoded[:2] == [b"original", b"style"]
    assert len(images) == 3
    assert decoded[-1] == raw.getvalue()
    assert all(part["detail"] == "high" for part in images)
    assert "Judge the LAST full image" in content[-1]["text"]
    full_request = client.calls[1]["json"]["messages"]
    assert "ink_region_with_margin" not in json.dumps(full_request)
    assert "rectangle must be clear" not in full_request[0]["content"]
    assert "anatomy" in full_request[0]["content"]
    assert "identity" in full_request[0]["content"]


@pytest.mark.asyncio
async def test_title_suggestions_use_story_language_and_guidance(client):
    titles = [
        "Lia e o céu",
        "Lia na Lua",
        "As descobertas de Lia",
        "Lia e o cometa",
        "Lia astronauta",
    ]
    client.script = [(200, _ok(json.dumps({"titles": titles})))]
    result = await oai.OpenAITextProvider().suggest_titles(
        context={"title": "Lia", "story": "Lia voou até a Lua", "language": "pt-BR"},
        guidance="Mais aventura",
    )
    assert result == titles
    payload = client.calls[0]["json"]
    assert payload["response_format"] == {"type": "json_object"}
    supplied = json.loads(payload["messages"][1]["content"])
    assert supplied["context"]["story"] == "Lia voou até a Lua"
    assert supplied["context"]["language"] == "pt-BR"
    assert supplied["editorial_guidance"] == "Mais aventura"


def test_default_pause_prevents_unapproved_credit_spending():
    from app.config import Settings

    assert Settings.model_fields["skip_openai"].default is True


@pytest.mark.asyncio
async def test_title_suggestions_do_not_return_demo_titles(client, monkeypatch):
    monkeypatch.setattr(oai.settings, "skip_openai", True)
    with pytest.raises(ProviderError):
        await oai.OpenAITextProvider().suggest_titles(context={"title": "Lia"})
    assert client.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "titles",
    [
        ["Um", "Dois"],
        ["Igual"] * 5,
        ["Lia", "A", "B", "C", "D"],
        ["A", "B", "C", "D", "x" * 121],
        ["A", "B", "C", "D", None],
    ],
)
async def test_title_suggestions_reject_bad_ai_output_without_inventing_replacements(
    client, titles
):
    client.script = [(200, _ok(json.dumps({"titles": titles})))]
    with pytest.raises(ProviderError):
        await oai.OpenAITextProvider().suggest_titles(context={"title": "Lia"})


class _FakeResponse:
    def __init__(self, status_code: int, json_data: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text or (json.dumps(self._json) if json_data else f"status {status_code}")
        self.headers = {"x-request-id": "req-test-moderation"}

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
    assert call["headers"]["X-Client-Request-Id"]
    assert call["json"]["messages"][0]["role"] == "system"
    assert "Luna e a floresta" in call["json"]["messages"][1]["content"]
    assert result.text.startswith("Título:")
    assert result.meta["provider"] == "openai"
    assert result.cost_usd > 0


@pytest.mark.asyncio
async def test_moderation_preflight_is_free_and_sends_text_and_authorized_photo(client):
    photo = io.BytesIO()
    Image.new("RGB", (8, 8), "blue").save(photo, "PNG")
    client.script = [(200, {"results": [{"flagged": False, "categories": {}}]})]

    result = await oai.OpenAITextProvider().moderate_book_input(
        text='{"theme":"stars"}', photos=[photo.getvalue()]
    )

    call = client.calls[0]
    assert call["url"].endswith("/moderations")
    assert call["json"]["model"] == "omni-moderation-latest"
    assert call["json"]["input"][0] == {"type": "text", "text": '{"theme":"stars"}'}
    image = call["json"]["input"][1]
    assert image["type"] == "image_url"
    image_url = image["image_url"]["url"]
    assert image_url.startswith("data:image/jpeg;base64,")
    normalized = base64.b64decode(image_url.split(",", 1)[1])
    with Image.open(io.BytesIO(normalized)) as sent_image:
        assert sent_image.format == "JPEG"
        assert sent_image.size == (8, 8)
    assert result.meta["flagged"] is False
    assert result.cost_usd == 0
    assert result.meta["request_id"] == "req-test-moderation"
    assert result.meta["client_request_id"] == call["headers"]["X-Client-Request-Id"]


@pytest.mark.asyncio
async def test_moderation_preflight_reports_flagged_input_without_chat_completion(client):
    client.script = [(200, {"results": [{"flagged": True, "categories": {"violence": True}}]})]

    result = await oai.OpenAITextProvider().moderate_book_input(text="unsafe", photos=[])

    assert result.meta["flagged"] is True
    assert result.cost_usd == 0
    assert len(client.calls) == 1
    assert client.calls[0]["url"].endswith("/moderations")


@pytest.mark.asyncio
async def test_moderation_preflight_fails_closed_on_invalid_result_schema(client):
    client.script = [(200, {"results": [{"categories": {}}]})]

    with pytest.raises(ProviderError, match="INPUT_SAFETY_CHECK_INVALID"):
        await oai.OpenAITextProvider().moderate_book_input(text="sample", photos=[])


@pytest.mark.asyncio
async def test_moderation_preflight_rejects_corrupt_photo_before_network_call(client):
    with pytest.raises(ProviderError, match="INPUT_SAFETY_CHECK_INVALID_IMAGE"):
        await oai.OpenAITextProvider().moderate_book_input(text="sample", photos=[b"bad"])
    assert client.calls == []


@pytest.mark.asyncio
async def test_ambiguous_text_timeout_is_not_marked_safe_to_retry(client, monkeypatch):
    class ReadTimeoutClient(_FakeAsyncClient):
        async def post(self, url, json=None, headers=None):
            self.calls.append({"url": url, "json": json, "headers": headers})
            raise httpx.ReadTimeout("response timed out")

    monkeypatch.setattr(oai.httpx, "AsyncClient", ReadTimeoutClient)
    with pytest.raises(ProviderError) as caught:
        await oai.OpenAITextProvider().generate_story(brief="Luna", style="cartoon", pages=1)
    assert caught.value.outcome_unknown is True
    assert caught.value.retry_safe is False
    assert caught.value.client_request_id
    assert len(ReadTimeoutClient.calls) == 1


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
    payload = client.calls[0]["json"]
    assert payload["response_format"] == {"type": "json_object"}
    guidance = payload["messages"][0]["content"]
    assert "maiúsculas, acentos e pontuação" in guidance
    assert "2 a 4 linhas curtas" in guidance
    assert "Evite moralismo" in guidance
    parts = payload["messages"][1]["content"]
    assert parts[0]["type"] == "image_url"
    assert parts[0]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert parts[1]["type"] == "text"


@pytest.mark.asyncio
async def test_editorial_profile_creates_theme_title_and_limits_cast(client):
    from app.services import editorial_profile

    policy = json.loads(
        (editorial_profile._root() / "config/editorial-policy.json").read_text(encoding="utf-8")
    )
    expected = {"locales": {"pt-BR": {"title": "Carlos e as Cores do Jardim"}}}
    client.script = [(200, _ok(json.dumps(expected)))]
    result = await oai.OpenAITextProvider().prepare_book_profile(
        ficha={
            "name": "Carlos",
            "title": "",
            "theme": "Aprender a cuidar das plantas",
            "characters": {"names": "", "photos": []},
            "languages": ["pt-BR"],
            "editorial_policy": policy,
        },
        photos=[b"original"],
    )
    guidance = client.calls[0]["json"]["messages"][0]["content"]
    assert "Se ficha.title estiver vazio" in guidance
    assert "criativo e específico" in guidance
    assert "Pessoas no fundo das fotos não são acompanhantes" in guidance
    assert "apenas o protagonista" in guidance
    assert json.loads(result.text) == expected


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

    client.script = [(429, {"error": {"code": "credit_balance_exhausted"}})]
    client.calls.clear()
    with pytest.raises(ProviderError, match="credit_balance_exhausted") as blocked:
        await oai.OpenAITextProvider().generate_story(brief="x", style="s", pages=1)
    assert blocked.value.transient is False


def test_factory_text_provider_is_openai():
    assert get_text_provider("openai").name == "openai"
    assert get_text_provider("claude").name == "openai"


@pytest.mark.asyncio
async def test_rehearsal_text_skips_openai(monkeypatch):
    monkeypatch.setattr(oai.settings, "skip_openai", True)
    result = await oai.OpenAITextProvider(api_key="").generate_story(brief="x", style="s", pages=2)
    assert result.meta["provider"] == "demo"
    assert result.cost_usd == 0
    assert "Página 1" in result.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "report",
    [
        {"valid": False, "issues": ["hair in reserve"], "limitations": []},
        {"valid": True, "issues": ["hand in reserve"], "limitations": []},
        {"valid": False, "issues": [], "limitations": ["inconclusive"]},
    ],
)
async def test_failed_reserve_never_advances_to_full_review(client, report):
    client.script = [(200, _ok(json.dumps(report)))]
    raw = io.BytesIO()
    Image.new("RGB", (100, 100), "blue").save(raw, "PNG")
    result = await oai.OpenAITextProvider().validate_editorial_preview(
        data=raw.getvalue(),
        photos=[b"identity"],
        cover=None,
        prompt="ARTE_BASE: scene",
        style_refs=[],
        inspection_region=[0.1, 0.1, 0.9, 0.3],
    )
    assert len(client.calls) == 1
    assert json.loads(result.text) == report
    assert result.meta["review_scope"] == "text_reserve"


@pytest.mark.asyncio
async def test_clear_crop_does_not_override_failed_identity_review(client):
    good = {"valid": True, "issues": [], "limitations": []}
    bad = {"valid": False, "issues": ["Identity differs"], "limitations": []}
    client.script = [(200, _ok(json.dumps(good))), (200, _ok(json.dumps(bad)))]
    raw = io.BytesIO()
    Image.new("RGB", (100, 100), "blue").save(raw, "PNG")
    result = await oai.OpenAITextProvider().validate_editorial_preview(
        data=raw.getvalue(),
        photos=[b"identity"],
        cover=None,
        prompt="ARTE_BASE: rectangle must be clear ink_region_with_margin",
        style_refs=[],
        inspection_region=[0.1, 0.1, 0.9, 0.3],
        full_image_prompt="ARTE_BASE: requested scene and outfit",
    )
    assert len(client.calls) == 2
    assert json.loads(result.text) == bad
    full_prompt = json.dumps(client.calls[1]["json"]["messages"])
    assert "ink_region_with_margin" not in full_prompt
    assert "requested scene and outfit" in full_prompt
