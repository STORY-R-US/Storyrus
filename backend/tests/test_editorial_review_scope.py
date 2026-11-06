"""Flat intermediates use their own visual review contract."""

import json
from types import SimpleNamespace

import pytest

from app.ai_clients.base import TextResult
from app.services import editorial_profile
from app.workers.handlers.editorial_book import Pipeline


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["ARTE_BASE", "CAPA_PLANA", "PAGINA_INTERNA"])
async def test_flat_review_contract(role):
    captured = []

    async def validate(**kwargs):
        captured.append(kwargs["prompt"])
        return TextResult(
            text=json.dumps({"valid": True, "issues": [], "limitations": []}), cost_usd=0
        )

    pipe = object.__new__(Pipeline)
    pipe.demo = False
    pipe.guard = lambda: None
    pipe.account = lambda *args: None
    pipe.profile = {"editorial": editorial_profile.snapshot()}
    pipe.policy = editorial_profile.policy(pipe.profile)
    pipe.base = {"reference_manifest": []}
    pipe.photos = []
    pipe.refs = []
    pipe.master = SimpleNamespace(
        _pkg=lambda: SimpleNamespace(
            get_text_provider=lambda: SimpleNamespace(validate_editorial_preview=validate)
        )
    )
    report = await pipe.review(b"image", role + ": contract", technical={})
    assert report["status"] == "valid"
    assert "Verifique capa quadrada e cada" not in captured[0]
    assert "ARTE_BASE deve ser" in captured[0]
    assert "CAPA_PLANA e PAGINA_INTERNA" in captured[0]
