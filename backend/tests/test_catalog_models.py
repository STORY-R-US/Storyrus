import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from PIL import Image

from app.schemas import PreviewRequestIn
from app.services import book_design, editorial_profile
from app.workers import editorial_render as render

MODELS = book_design.definitions(4)["models"]


@pytest.mark.parametrize("model", list(MODELS))
def test_each_available_catalog_book_has_its_own_frozen_references_and_layout(model):
    design = book_design.snapshot(model)
    assert design["version"] == 4
    assert book_design.resolve({"book_design": design}) == design
    assert design["catalog_index"] == int(model.rsplit("-", 1)[1])
    for role in ("cover", "page", "holding"):
        with Image.open(io.BytesIO(book_design.reference(design, role))) as image:
            image.verify()
    assert design["reference_sha256"]["cover"] != design["reference_sha256"]["page"]
    profile = {"editorial": editorial_profile.snapshot(), "book_design": design}
    title = design["title_templates"]["pt-BR"].replace(design.get("example_name") or "\0", "João")
    _, layout = render.text(
        render.encode(Image.new("RGB", (1024, 1024), "ivory")),
        title,
        profile,
        title=True,
        measure_only=True,
    )
    assert layout["text"] == title
    assert layout["region"] == design["cover"]["region"]


@pytest.mark.parametrize(
    "model", ["catalog-realistic-0", "catalog-realistic-1", "catalog-realistic-6"]
)
def test_catalog_title_changes_only_name_while_theme_remains_free(model):
    project = SimpleNamespace(
        book_profile={"stage": "ficha"},
        style="realistic",
        theme="Aventura espacial",
        child_name="João",
        language="pt-BR",
    )
    selected = book_design.select(project, model)
    expected = selected["title_templates"]["pt-BR"].replace(
        selected["example_name"] or "\0", "João"
    )
    assert project.book_profile["title"] == expected
    assert project.theme == "Aventura espacial"
    assert project.book_profile["supplied_locales"]["en"]["title"] == selected["title_templates"][
        "en"
    ].replace(selected["example_name"] or "\0", "João")
    assert book_design.select(project, "auto") == selected


@pytest.mark.parametrize("model", list(book_design.definitions(4)["unavailable"]))
def test_missing_interior_is_blocked_before_generation(model):
    assert PreviewRequestIn(catalog_design_id=model).catalog_design_id == model
    with pytest.raises(HTTPException) as err:
        book_design.snapshot(model)
    assert err.value.status_code == 409
    assert "miolo" in err.value.detail


def test_catalog_registry_matches_frontend_availability_and_reference_sources():
    web = json.loads(
        (Path(__file__).parents[2] / "apps/web/src/catalogModels.json").read_text(encoding="utf8")
    )
    assert set(MODELS) == {k for k, v in web.items() if v["available"]}
    assert set(book_design.definitions(4)["unavailable"]) == {
        k for k, v in web.items() if not v["available"]
    }
    for key, design in MODELS.items():
        assert design["sources"] == web[key]["sources"]


@pytest.mark.parametrize("index", [0, 1, 2, 9, 10, 18, 21, 60, 62, 63, 64, 65, 66, 67])
def test_new_cartoon_interiors_have_square_pages_and_valid_narrative_font(index):
    design = book_design.snapshot(f"catalog-cartoon-{index}")
    assert design["style"] == "cartoon"
    assert design["interior"]["mode"] == (
        "text_left" if index in (0, 1, 2, 9, 10) else "two_scenes"
    )
    with Image.open(io.BytesIO(book_design.reference(design, "page"))) as image:
        assert image.width / image.height == pytest.approx(2, abs=0.01)
    with Image.open(io.BytesIO(book_design.reference(design, "cover"))) as image:
        assert image.width == image.height
    profile = {"editorial": editorial_profile.snapshot(), "book_design": design}
    _, layout = render.text(
        render.encode(Image.new("RGB", (1024, 1024), "ivory")),
        "Cada aventura traz carinho e atenção.",
        profile,
        title=False,
        measure_only=True,
    )
    assert layout["text"] == "Cada aventura traz carinho e atenção."


def test_exact_selected_models_are_distinct_and_generic_default_is_unchanged():
    mother = book_design.snapshot("catalog-realistic-6")
    emilia = book_design.snapshot("catalog-realistic-1")
    martin = book_design.snapshot("catalog-realistic-0")
    assert mother["interior"]["mode"] == "text_right"
    assert emilia["typography"]["titleFontFile"] == "BreeSerif-Regular.ttf"
    assert martin["typography"]["titleColor"] != mother["typography"]["titleColor"]
    assert book_design.snapshot("adventure")["version"] == 3
    for model in (mother, emilia, martin):
        prompt = book_design.prompt(model, "cover", "João observa estrelas")
        assert "João observa estrelas" in prompt
        assert "The user may change the story theme" in prompt


@pytest.mark.parametrize(
    "model", ["catalog-realistic-6", "catalog-realistic-1", "catalog-realistic-0"]
)
def test_richer_scenery_preserves_the_selected_reading_page_contract(model):
    design = book_design.snapshot(model)
    for role in ("cover", "illustration_page", "holding"):
        prompt = book_design.prompt(design, role, "Lia explora a praia")
        assert "SCENE DETAIL AND DEPTH" in prompt
        assert "Lia explora a praia" in prompt
        assert design["sha256"] in prompt
    reading = book_design.prompt(design, "reading_page", "Página de leitura")
    assert "SCENE DETAIL AND DEPTH" not in reading
    assert "READING PAGE DETAIL" in reading


def test_custom_club_title_survives_catalog_selection_and_retry():
    project = SimpleNamespace(
        book_profile={"stage": "ficha", "title": "João, goleiro do Palmeiras"},
        style="realistic",
        theme="Futebol",
        child_name="João",
        language="pt-BR",
    )
    for model in ("catalog-realistic-0", "catalog-realistic-0", "auto"):
        book_design.select(project, model)
        assert project.book_profile["title"] == "João, goleiro do Palmeiras"
        assert (
            project.book_profile["supplied_locales"]["pt-BR"]["title"]
            == project.book_profile["title"]
        )
    assert project.book_profile["book_design"]["id"] == "catalog-realistic-0"


@pytest.mark.parametrize("style", ["realistic", "cartoon"])
@pytest.mark.parametrize("language", ["pt-BR", "en", "es"])
def test_couple_names_replace_localized_examples_in_every_title(style, language):
    project = SimpleNamespace(
        book_profile={"stage": "ficha"},
        style=style,
        theme="casamento",
        child_name="Ana & Pedro",
        language=language,
    )
    book_design.select(project, f"catalog-{style}-67")
    expected = {
        "pt-BR": "Ana & Pedro, Nosso Sim para Sempre",
        "en": "Ana & Pedro, Our Forever Yes",
        "es": "Ana & Pedro, Nuestro Sí para Siempre",
    }
    assert project.book_profile["title"] == expected[language]
    assert {
        key: value["title"] for key, value in project.book_profile["supplied_locales"].items()
    } == expected
    book_design.select(project, "auto")
    assert project.book_profile["title"] == expected[language]
    project.book_profile["title"] = "Ana & Pedro: Our Story"
    book_design.select(project, f"catalog-{style}-67")
    assert all(
        value["title"] == "Ana & Pedro: Our Story"
        for value in project.book_profile["supplied_locales"].values()
    )
