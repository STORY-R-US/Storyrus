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


def test_studio_title_suggestions_use_the_typed_theme(auth_client, monkeypatch):
    calls = []

    async def suggest(self, **kwargs):
        calls.append(kwargs)
        return [f"Lia e o fundo do mar {i}" for i in range(5)]

    monkeypatch.setattr(oai.OpenAITextProvider, "suggest_titles", suggest)
    response = auth_client.post(
        "/v1/studio/title/suggest",
        json={"theme": "  Lia   no fundo do mar ", "name": "Lia", "age": 5, "language": "pt-BR"},
    )
    assert response.status_code == 200, response.text
    assert len(response.json()["titles"]) == 5
    assert calls[0]["context"]["theme"] == "Lia no fundo do mar"
    assert calls[0]["context"]["protagonist"] == "Lia"
    assert auth_client.post("/v1/studio/title/suggest", json={}).status_code == 422


def test_studio_title_suggestions_hide_errors_and_need_login(auth_client, client, monkeypatch):
    async def broken(self, **kwargs):
        raise ProviderError("secret upstream error")

    monkeypatch.setattr(oai.OpenAITextProvider, "suggest_titles", broken)
    response = auth_client.post("/v1/studio/title/suggest", json={"theme": "mar"})
    assert response.status_code == 502
    assert "secret" not in response.text
    assert client.post("/v1/studio/title/suggest", json={"theme": "mar"}).status_code in {401, 403}


def test_dedication_suggestions_understand_the_book(auth_client, monkeypatch):
    calls = []

    async def write(self, **kwargs):
        calls.append(kwargs)
        return ["Para Lia, que ama o mar.", "Lia, mergulhe nos sonhos.", "Com amor, para Lia."]

    monkeypatch.setattr(oai.OpenAITextProvider, "write_dedications", write)
    response = auth_client.post(
        "/v1/studio/dedication/suggest",
        json={"name": "Lia", "age": 5, "theme": "fundo do mar", "title": "Lia e o Mar"},
    )
    assert response.status_code == 200, response.text
    assert len(response.json()["dedications"]) == 3
    assert calls[0]["context"]["theme"] == "fundo do mar"
    assert calls[0]["context"]["title"] == "Lia e o Mar"
    assert auth_client.post("/v1/studio/dedication/suggest", json={}).status_code == 422


@pytest.mark.asyncio
async def test_provider_validates_three_dedications(monkeypatch):
    monkeypatch.setattr(oai.settings, "skip_openai", False)
    answers = [
        json.dumps({"dedications": ["Para Lia.", "Com amor, Lia.", "Lia, sonhe alto."]}),
        json.dumps({"dedications": ["Para Lia.", "Para Lia.", "Para Lia."]}),
    ]

    async def complete(self, **kwargs):
        return TextResult(text=answers.pop(0))

    monkeypatch.setattr(oai.OpenAITextProvider, "_complete", complete)
    provider = oai.OpenAITextProvider(api_key="test")
    assert len(await provider.write_dedications(context={"child_name": "Lia"})) == 3
    with pytest.raises(ProviderError):
        await provider.write_dedications(context={"child_name": "Lia"})
