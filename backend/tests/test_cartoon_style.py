"""Cartoon references must guide rendering without replacing customer identity."""

from types import SimpleNamespace

import pytest

from app.ai_clients.base import ImageResult
from app.ai_clients.book_prompts import AVATAR_PROMPT, book_art_direction
from app.ai_clients.image_openai import OpenAIImageProvider
from app.services import book_design, book_profile, cartoon_style


@pytest.mark.parametrize(
    "value",
    [
        "cartoon",
        "Cartoon 3D premium",
        book_art_direction("cartoon"),
        book_profile.art_direction("cartoon"),
    ],
)
def test_cartoon_direction_is_recognized(value):
    assert cartoon_style.applies(value)


@pytest.mark.parametrize(
    "value",
    [
        "realistic",
        "fotografia editorial natural; capa preserva acabamento original",
        book_art_direction("realistic"),
        book_profile.art_direction("realistic"),
    ],
)
def test_realistic_and_reading_remain_photographic(value):
    assert not cartoon_style.applies(value)
    assert cartoon_style.inputs("original", [b"photo"], value) == ("original", [b"photo"])


def test_character_and_catalog_policy_use_same_direction_without_changing_saved_design():
    project = SimpleNamespace(style="cartoon", child_name="Lia", child_age=6)
    assert cartoon_style.MARKER in book_profile.avatar_prompt(project)
    design = book_design.snapshot("catalog-cartoon-8")
    assert cartoon_style.reference() == book_design.reference(design, "cover")
    policy = {"visual": {}, "typography": {}, "referenceComposition": {}}
    book_design.apply_policy(design, policy)
    assert cartoon_style.MARKER in policy["visual"]["artDirection"]
    assert book_design.resolve({"book_design": design}) == design


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operation",
    [
        "character",
        "scene",
        "scene_photo",
        "refine_identity",
        "refine_scene",
        "refine_scene_photo",
        "fallback",
    ],
)
async def test_all_cartoon_paths_append_style_reference_after_identity(monkeypatch, operation):
    captured = {}

    async def capture(self, prompt, images, *, size):
        captured.update(prompt=prompt, images=images, size=size)
        return ImageResult(image_bytes=b"result", mime_type="image/png", cost_usd=0)

    monkeypatch.setattr(OpenAIImageProvider, "_generate_with_refs", capture)
    provider = OpenAIImageProvider()
    if operation == "character":
        await provider.generate_character(
            prompt=AVATAR_PROMPT, reference_images=[b"photo"], style="cartoon"
        )
        expected = [b"photo"]
    elif operation.startswith("scene"):
        photo = b"photo" if operation.endswith("photo") else None
        await provider.generate_scene(
            prompt="boat",
            character_ref=b"avatar",
            photo=photo,
            extra_refs=[b"wardrobe"],
            style="cartoon",
            landscape=True,
        )
        expected = ([b"photo"] if photo else []) + [b"avatar", b"wardrobe"]
        assert captured["size"] == "1536x1024"
    elif operation == "refine_identity":
        await provider.refine_identity(photo=b"photo", illustration=b"avatar", style="cartoon")
        expected = [b"photo", b"avatar"]
    elif operation.startswith("refine_scene"):
        photo = b"photo" if operation.endswith("photo") else None
        await provider.refine_scene(
            character_ref=b"avatar", scene=b"scene", photo=photo, style="cartoon"
        )
        expected = ([b"photo"] if photo else []) + [b"avatar", b"scene"]
    else:
        await provider.generate_realistic(photo=b"photo", prompt="character", style="cartoon")
        expected = [b"photo"]
    assert captured["images"] == [*expected, cartoon_style.reference()]
    assert cartoon_style.MARKER in captured["prompt"]
    assert "ULTIMA IMAGEM: referencia de ESTILO" in captured["prompt"]
    assert "Photorealistic digital painting" not in captured["prompt"]
    assert "ROSTO REALISTA" not in captured["prompt"]


@pytest.mark.asyncio
async def test_photographic_holding_does_not_get_cartoon_cast(monkeypatch):
    captured = {}

    async def capture(self, prompt, images, *, size):
        captured.update(prompt=prompt, images=images)
        return ImageResult(image_bytes=b"result", mime_type="image/png", cost_usd=0)

    monkeypatch.setattr(OpenAIImageProvider, "_generate_with_refs", capture)
    await OpenAIImageProvider().generate_scene(
        prompt="Read the approved Cartoon book",
        character_ref=b"cover",
        photo=b"photo",
        style="fotografia editorial natural; capa preserva acabamento original",
        reference_role="cover",
    )
    assert captured["images"] == [b"photo", b"cover"]
    assert cartoon_style.MARKER not in captured["prompt"]
