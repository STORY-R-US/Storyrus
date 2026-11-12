import json
from types import SimpleNamespace

import pytest

from app.services import book_design, scene_richness
from app.workers.handlers.editorial_book import Pipeline

MODELS = [book_design.snapshot(key) for key in book_design.definitions(4)["models"]]


@pytest.mark.parametrize("design", MODELS, ids=lambda item: item["id"])
@pytest.mark.parametrize("role", ["cover", "illustration", "reading", "expansion"])
def test_every_catalog_model_retains_finish_layout_and_safe_reading_area(design, role):
    region = design["cover" if role == "cover" else "interior"]["region"]
    action = "A protagonista observa conchas na praia"
    output = scene_richness.direction(
        theme="praia", action=action, role=role, design=design, text_region=region
    )
    contract = json.loads(output.split(": ", 1)[1])
    assert contract["family"] == "beach"
    assert contract["finish"] == design["finish"]
    assert contract["text_region"] == region
    assert contract["current_action"] == action
    assert "hair" in contract["protection"] and "hats" in contract["protection"]
    if role == "reading":
        assert "OUTSIDE the entire reading rectangle" in contract["composition"]
        assert "no scene or people" in contract["composition"]
    else:
        assert "foreground, action plane and distant background" in contract["composition"]


@pytest.mark.parametrize("name,entry", scene_richness.FAMILIES.items())
def test_every_theme_keyword_resolves_to_its_own_family(name, entry):
    for keyword in entry[0].split():
        assert scene_richness.family(keyword) == name


@pytest.mark.parametrize(
    "theme,expected",
    [
        ("Balé", "ballet"),
        ("futebol", "football"),
        ("praia", "beach"),
        ("espaço", "space"),
        ("cerâmica artesanal", "custom"),
    ],
)
def test_explicit_customer_theme_wins_over_catalog_sample_and_old_title(theme, expected):
    pipe = SimpleNamespace(
        profile={"theme_description": theme, "title": "Martin, Goleiro do Chile"},
        project=SimpleNamespace(theme="sport"),
        design=MODELS[0],
    )
    contract = json.loads(
        Pipeline.scenery_direction(pipe, "A nova aventura", "cover", [0.1, 0.05, 0.9, 0.3]).split(
            ": ", 1
        )[1]
    )
    assert contract["family"] == expected
    assert "goal-net" not in contract["conditional_material_cues"] or expected == "football"


def test_custom_theme_is_not_replaced_with_a_catalog_story():
    output = scene_richness.direction(
        theme="cerâmica artesanal", action="modelar argila", role="illustration"
    )
    contract = json.loads(output.split(": ", 1)[1])
    assert contract["family"] == "custom"
    assert contract["current_action"] == "modelar argila"
    assert "customer's theme" in contract["conditional_material_cues"]


@pytest.mark.parametrize("role", ["cover", "illustration", "expansion"])
def test_naturalism_preserves_identity_age_and_physical_scene_without_forcing_finish(role):
    output = scene_richness.direction(
        theme="aeroclube",
        action="Os primos brincam no avião parado",
        role=role,
        design={"id": "cartoon", "finish": "gentle cartoon"},
        text_region=[0.1, 0.05, 0.9, 0.3],
    )
    contract = json.loads(output.split(": ", 1)[1])
    assert contract["family"] == "aviation"
    assert contract["finish"] == "gentle cartoon"
    naturalism = contract["naturalism"]
    assert "not instructions for the new scene" in naturalism["identity_scope"]
    assert "never clone" in naturalism["identity_scope"]
    assert "age-appropriate" in naturalism["anatomy"]
    assert "do not force photorealism" in naturalism["anatomy"]
    assert "supporting surface" in naturalism["physical_support"]
    assert "one coherent lighting direction" in naturalism["light_and_depth"]
    assert "do not add cast or change the story" in naturalism["environment"]
