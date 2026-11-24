import json

import pytest

from app.ai_clients import text_openai as oai
from app.ai_clients.base import ProviderError, TextResult


def test_improve_dedication_returns_ai_text(auth_client, monkeypatch):
    calls = []

    async def improve(self, **kwargs):
        calls.append(kwargs)
        return "Para Lia, com todo o amor da mamãe."

    monkeypatch.setattr(oai.OpenAITextProvider, "improve_dedication", improve)
    response = auth_client.post(
        "/v1/studio/dedication/improve",
        json={"text": "  te amo   lia ", "name": "Lia", "language": "pt-BR"},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"dedication": "Para Lia, com todo o amor da mamãe."}
    assert calls == [{"text": "te amo lia", "name": "Lia", "language": "pt-BR"}]


def test_improve_dedication_hides_provider_errors_and_needs_login(auth_client, client, monkeypatch):
    async def broken(self, **kwargs):
        raise ProviderError("secret upstream error")

    monkeypatch.setattr(oai.OpenAITextProvider, "improve_dedication", broken)
    response = auth_client.post("/v1/studio/dedication/improve", json={"text": "te amo"})
    assert response.status_code == 502
    assert "secret" not in response.text
    assert auth_client.post("/v1/studio/dedication/improve", json={"text": ""}).status_code == 422


def test_improve_dedication_requires_an_account(client):
    response = client.post("/v1/studio/dedication/improve", json={"text": "te amo"})
    assert response.status_code in {401, 403}


@pytest.mark.asyncio
async def test_provider_validates_the_ai_answer(monkeypatch):
    monkeypatch.setattr(oai.settings, "skip_openai", False)
    answers = [
        json.dumps({"dedication": "Para Lia, com amor."}),
        json.dumps({"dedication": "x" * 201}),
    ]

    async def complete(self, **kwargs):
        return TextResult(text=answers.pop(0))

    monkeypatch.setattr(oai.OpenAITextProvider, "_complete", complete)
    provider = oai.OpenAITextProvider(api_key="test")
    assert await provider.improve_dedication(text="te amo", name="Lia") == "Para Lia, com amor."
    with pytest.raises(ProviderError):
        await provider.improve_dedication(text="te amo", name="Lia")


@pytest.mark.asyncio
async def test_provider_is_off_when_openai_is_paused(monkeypatch):
    monkeypatch.setattr(oai.settings, "skip_openai", True)
    with pytest.raises(ProviderError):
        await oai.OpenAITextProvider().improve_dedication(text="te amo")
