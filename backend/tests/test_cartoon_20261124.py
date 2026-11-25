"""Cartoon expansion: immutable existing projects and complete localized models."""

from types import SimpleNamespace

import pytest

from app.services import book_design

INDEXES = range(69, 119)


def test_v6_only_adds_the_fifty_cartoon_editions():
    old = book_design.definitions(5)
    new = book_design.definitions(6)
    assert new["unavailable"] == old["unavailable"]
    assert set(new["models"]) - set(old["models"]) == {
        f"catalog-cartoon-{index}" for index in INDEXES
    }
    for key, model in old["models"].items():
        assert new["models"][key] == model


@pytest.mark.parametrize("model", ["catalog-realistic-69", "catalog-cartoon-8"])
def test_existing_v5_projects_keep_approved_design_and_calibration(model):
    frozen = book_design.snapshot(model, version=5)
    project = SimpleNamespace(
        style=frozen["style"],
        book_profile={"book_design": frozen, "cover_calibration": {"sha256": "approved"}},
    )
    assert book_design.select(project, "auto") == frozen
    assert book_design.select(project, model) == frozen
    assert book_design.resolve(project.book_profile) == frozen
    assert project.book_profile["cover_calibration"] == {"sha256": "approved"}


@pytest.mark.parametrize("index", INDEXES)
def test_new_cartoon_preserves_book_identity_and_uses_its_own_three_references(index):
    design = book_design.snapshot(f"catalog-cartoon-{index}")
    realistic = book_design.snapshot(f"catalog-realistic-{index}")
    assert design["version"] == 6
    assert design["style"] == "cartoon"
    assert design["title_templates"] == realistic["title_templates"]
    assert design["example_name"] == realistic["example_name"]
    assert design["interior"]["mode"] == "two_scenes"
    assert design["visual"]["finish"] == "amor_de_bisavo_cartoon"
    assert design["typography"] == realistic["typography"]
    for role in ("cover", "page", "holding"):
        assert design["reference_files"][role] == (
            f"catalog_models/cartoon-{index}-{role}-20261124.webp"
        )
        assert design["reference_sha256"][role] != realistic["reference_sha256"][role]


@pytest.mark.parametrize("language", ["pt-BR", "en", "es"])
def test_new_cartoon_selection_personalizes_all_languages(language):
    project = SimpleNamespace(
        style="cartoon",
        language=language,
        child_name="João",
        theme="A aventura escolhida",
        book_profile={"stage": "ficha"},
    )
    selected = book_design.select(project, "catalog-cartoon-69")
    assert project.book_profile["title"] == selected["title_templates"][language].replace(
        "Léo", "João"
    )
    assert project.theme == "A aventura escolhida"
    assert all(
        "João" in value["title"] for value in project.book_profile["supplied_locales"].values()
    )
