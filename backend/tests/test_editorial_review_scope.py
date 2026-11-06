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


@pytest.mark.parametrize("designed", [False, True])
def test_interior_overlap_uses_one_reframe_before_regenerating(designed):
    pipe = object.__new__(Pipeline)
    pipe.designed = designed
    pipe.last_art = b"existing candidate"
    pipe.last_review_issues = ["Head overlaps ink_region_with_margin"]
    assert not pipe.should_reframe_art(title=False, attempt=1)
    assert pipe.should_reframe_art(title=False, attempt=2)
    assert not pipe.should_reframe_art(title=False, attempt=3)
    pipe.last_review_issues = ["Identity differs from the reference photograph"]
    assert not pipe.should_reframe_art(title=False, attempt=2)
    pipe.last_review_issues = ["Head overlaps ink_region_with_margin"]
    pipe.last_art = None
    assert not pipe.should_reframe_art(title=False, attempt=2)


@pytest.mark.parametrize(
    "issues",
    [
        ["Visible hair", "Visible part of a face", "Visible ear"],
        ["Unspecified crop defect"],
        [],
    ],
)
def test_text_reserve_scope_triggers_reframe_without_keyword_matching(issues):
    pipe = object.__new__(Pipeline)
    pipe.designed = True
    pipe.last_art = b"rejected scene"
    pipe.last_review_scope = "text_reserve"
    pipe.last_review_issues = issues
    assert pipe.should_reframe_art(title=False, attempt=2)
    assert not pipe.should_reframe_art(title=False, attempt=1)
    assert not pipe.should_reframe_art(title=False, attempt=3)
