from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app import storage
from app.ai_clients.base import ProviderError
from app.services import book_design
from app.workers.handlers import editorial_book as module
from app.workers.handlers.editorial_book import Pipeline, VisualReviewError


def pipeline(monkeypatch, *, photos=1):
    pipe = object.__new__(Pipeline)
    pipe.demo = False
    pipe.designed = True
    pipe.design = None
    pipe.photos = [f"original-photo-{i}".encode() for i in range(photos)]
    pipe.language = "pt"
    pipe.reference_theme = "football"
    pipe.profile = {
        "editorial": {"version": 1},
        "locales": {"pt": {"title": "João, Goleiro do Palmeiras"}},
    }
    pipe.base = {
        "cast_contract": {"protagonist": "original"},
        "reference_manifest": [],
        "continuity": {"costume": "blue shirt"},
    }
    pipe.cover_continuity = b"approved-cover"
    pipe.project = SimpleNamespace(
        id="project", book_profile=pipe.profile, style="cartoon", book_size="M"
    )
    pipe.job = SimpleNamespace(id="job", result={})
    pipe.policy = {"production": {"retryPolicy": {"proposedDefaultMaxRetriesAfterFirstAttempt": 2}}}
    assets, saved = [], {}
    pipe.db = SimpleNamespace(
        add=assets.append,
        commit=lambda: None,
        scalars=lambda _: SimpleNamespace(all=lambda: assets),
    )
    pipe.cached = lambda key: next((a for a in assets if a.storage_key == key), None)
    pipe.guard = lambda **_: None
    pipe.account = lambda *_: None
    pipe.record = lambda *_args, **_kwargs: None
    pipe.revision_for = lambda _: {}
    pipe.review = AsyncMock(return_value={"status": "valid"})
    provider = SimpleNamespace(
        generate_scene=AsyncMock(return_value=SimpleNamespace(image_bytes=b"complete-scene"))
    )
    pipe.master = SimpleNamespace(_pkg=lambda: SimpleNamespace(get_image_provider=lambda: provider))
    monkeypatch.setattr(module, "require_photo_authorization", lambda *_: None)
    monkeypatch.setattr(module.visual_reference, "load", lambda *_: b"catalog-presentation")
    monkeypatch.setattr(storage, "put_bytes", lambda key, data, _: saved.__setitem__(key, data))
    monkeypatch.setattr(storage, "get_bytes", saved.__getitem__)
    return pipe, provider, assets


@pytest.mark.asyncio
@pytest.mark.parametrize("photos", [1, 2, 3])
@pytest.mark.parametrize(
    "language,title",
    [("pt", "João, Goleiro do Palmeiras"), ("en", "João, My Hero!"), ("es", "¡João, Mi Héroe!")],
)
async def test_integrated_scene_uses_original_faces_finished_cover_and_literal_title(
    monkeypatch, photos, language, title
):
    pipe, provider, _ = pipeline(monkeypatch, photos=photos)
    pipe.language = language
    pipe.profile["locales"][language] = {"title": title}
    data, meta = await pipe.integrated_reading(b"finished-cover")
    args = provider.generate_scene.call_args.kwargs
    # generate_scene only prepends a secondary image when it differs from photo.
    assert args["character_ref"] == args["photo"] == pipe.photos[0]
    assert args["extra_refs"] == pipe.photos[1:] + [b"finished-cover", b"catalog-presentation"]
    assert f"Reference {photos + 1}" in args["prompt"]
    assert f"Reference {photos + 2}" in args["prompt"]
    assert title in args["prompt"]
    assert "#ff00ff" not in args["prompt"]
    assert args["style"] == "fotografia editorial natural"
    assert data == b"complete-scene"
    assert meta["presentation"] == "integrated_reading"
    assert pipe.review.call_args.kwargs["mandatory"] is True
    assert pipe.review.call_args.kwargs["cover"] == b"finished-cover"


@pytest.mark.asyncio
async def test_rejected_text_reuses_paid_scene_on_another_job(monkeypatch):
    pipe, provider, assets = pipeline(monkeypatch)
    pipe.review.side_effect = VisualReviewError("changed title", scope="full_image")
    with pytest.raises(VisualReviewError):
        await pipe.integrated_reading(b"finished-cover")
    assert len(assets) == 1  # persisted before review, never published as approved
    pipe.job = SimpleNamespace(id="new-job", result={})
    pipe.review.side_effect = None
    data, _ = await pipe.integrated_reading(b"finished-cover")
    assert data == b"complete-scene"
    assert provider.generate_scene.await_count == 1


@pytest.mark.asyncio
async def test_unknown_result_cannot_switch_to_legacy_or_repurchase(monkeypatch):
    pipe, provider, _ = pipeline(monkeypatch)
    provider.generate_scene.side_effect = ProviderError(
        "timeout", outcome_unknown=True, retry_safe=False
    )
    for _ in range(2):
        with pytest.raises(ProviderError):
            await pipe.integrated_reading(b"finished-cover")
    assert provider.generate_scene.await_count == 1
    assert pipe.integrated_reading_available() is True


@pytest.mark.parametrize("legacy", ["asset", "job", "unknown"])
def test_saved_or_uncertain_legacy_work_is_not_migrated(monkeypatch, legacy):
    pipe, _, _ = pipeline(monkeypatch)
    entries = {
        "asset": SimpleNamespace(meta={"stage": "reading:template"}),
        "job": SimpleNamespace(
            meta={}, result={"editorial_tasks": {"reading:template": {"state": "running"}}}
        ),
        "unknown": SimpleNamespace(meta={}, result={}),
    }
    pipe.db.scalars = lambda _: SimpleNamespace(all=lambda: [entries[legacy]])
    if legacy == "unknown":
        pipe.profile["generation_outcomes_unknown"] = {"key": {"stage": "reading:template"}}
    assert pipe.integrated_reading_available() is False


@pytest.mark.asyncio
async def test_integrated_failure_never_silently_returns_book_only(monkeypatch):
    pipe, _, _ = pipeline(monkeypatch)
    pipe.integrated_reading_available = lambda: True
    pipe.integrated_reading = AsyncMock(side_effect=ProviderError("review failed"))
    pipe.book_only_fallback = AsyncMock()
    with pytest.raises(ProviderError):
        await pipe.mockup("reading", [b"cover"], cover=b"cover")
    pipe.book_only_fallback.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["family", "adventure", "cartoon"])
async def test_catalog_reading_has_no_contradictory_marker_instructions(monkeypatch, model):
    pipe, provider, _ = pipeline(monkeypatch)
    pipe.design = book_design.snapshot(model)
    monkeypatch.setattr(book_design, "reference", lambda *_: b"selected-model")
    await pipe.integrated_reading(b"approved-cover")
    args = provider.generate_scene.call_args.kwargs
    assert "COMPLETE CATALOG BOOK DESIGN" in args["prompt"]
    assert "carries the temporary marker" not in args["prompt"]
    assert "Render the approved cover directly" in args["prompt"]
    assert args["extra_refs"][-1] == b"selected-model"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role", ["cover", "page", "reading_page", "illustration_page", "open_book"]
)
async def test_every_editorial_role_is_integrated_and_resumes_without_repurchase(monkeypatch, role):
    pipe, provider, _ = pipeline(monkeypatch)
    monkeypatch.setattr(module.render, "square", lambda _: None)
    literal = (
        {"left": "João vê o céu.", "right": "É hora de voar!"}
        if role == "open_book"
        else ""
        if role == "illustration_page"
        else "João vê o céu."
    )
    first, meta = await pipe.integrated_editorial_scene(
        "cover" if role == "cover" else "preview:page", "watch the sky", role=role, text=literal
    )
    assert meta["integrated_text"] is True
    assert meta["layout"]["text"] == literal
    assert ("art_bytes" in meta) is (role != "open_book")
    args = provider.generate_scene.call_args.kwargs
    assert "INTEGRATED ART AND LETTERING" in args["prompt"]
    assert args["landscape"] is (role == "open_book")
    assert pipe.review.call_args.kwargs["mandatory"] is True
    pipe.job = SimpleNamespace(id="resumed", result={})
    second, _ = await pipe.integrated_editorial_scene(
        "cover" if role == "cover" else "preview:page", "watch the sky", role=role, text=literal
    )
    assert first == second
    assert provider.generate_scene.await_count == 1
    assert pipe.review.await_count == 1


@pytest.mark.parametrize("existing", ["none", "asset", "interrupted", "unknown"])
def test_workflow_freezes_before_first_purchase_and_preserves_old_projects(monkeypatch, existing):
    pipe, _, _ = pipeline(monkeypatch)
    pipe.db.scalar = lambda _: "saved" if existing == "asset" else None
    pipe.db.scalars = lambda _: SimpleNamespace(
        all=lambda: (
            [SimpleNamespace(result={"editorial_tasks": {"cover:art": {"state": "running"}}})]
            if existing == "interrupted"
            else []
        )
    )
    if existing == "unknown":
        pipe.profile["generation_outcomes_unknown"] = {"key": {"stage": "cover:art"}}
    assert pipe.integrated_editorial_available() is (existing == "none")
    if existing == "none":
        assert pipe.project.book_profile["scene_workflow"] == "integrated-v1"
        pipe.db.scalar = lambda _: "now-saved"
        assert pipe.integrated_editorial_available() is True


def test_reading_raw_and_final_share_the_requested_revision():
    pipe = object.__new__(Pipeline)
    pipe.project = SimpleNamespace(
        book_profile={
            "editorial_revisions": {"03_LEITURA": {"id": "edit", "adjustment": "natural pose"}}
        }
    )
    assert pipe.revision_for("reading:integrated") == pipe.revision_for("reading")
    assert pipe.revision_for("reading:template") == {}  # preserve legacy cache keys
