"""Compatibility and personalization gates for the approved photographic batch."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services import book_design, editorial_profile

UPDATED = set(range(62, 68))
INSERTED = set(range(69, 119))


def project(*, name="Ana & Pedro", language="pt-BR", title="", design=None):
    profile = {"stage": "ficha", "title": title}
    if design:
        profile["book_design"] = design
    return SimpleNamespace(
        book_profile=profile,
        style="realistic",
        theme="Uma história escolhida pela família",
        child_name=name,
        language=language,
    )


def test_new_registry_preserves_every_unrelated_and_cartoon_definition():
    previous = book_design.definitions(4)
    current = book_design.definitions(5)
    assert current["unavailable"] == previous["unavailable"]
    assert set(current["models"]) - set(previous["models"]) == {
        f"catalog-realistic-{index}" for index in INSERTED
    }
    for key, value in previous["models"].items():
        if key not in {f"catalog-realistic-{index}" for index in UPDATED}:
            assert current["models"][key] == value
    slugs = [current["models"][f"catalog-realistic-{index}"]["stable_slug"] for index in INSERTED]
    assert len(set(slugs)) == 50


@pytest.mark.parametrize("index", [21, 62, 65, 67, 68])
def test_existing_v4_project_keeps_its_original_snapshot_and_references(index):
    model = f"catalog-realistic-{index}"
    frozen = book_design.snapshot(model, version=4)
    existing = project(design=frozen)
    existing.book_profile["cover_calibration"] = {"sha256": "approved-cover"}
    assert book_design.resolve(existing.book_profile) == frozen
    assert book_design.select(existing, "auto") == frozen
    assert book_design.select(existing, model) == frozen
    assert existing.book_profile["book_design"]["version"] == 4
    assert existing.book_profile["cover_calibration"] == {"sha256": "approved-cover"}
    current = book_design.snapshot(model)
    assert current["version"] == book_design.CURRENT_CATALOG_VERSION
    if index in UPDATED:
        assert current["reference_files"] != frozen["reference_files"]
        assert current["reference_sha256"] != frozen["reference_sha256"]
    else:
        assert current["reference_sha256"] == frozen["reference_sha256"]


def test_existing_cartoon_v4_project_is_not_migrated_on_auto_selection():
    frozen = book_design.snapshot("catalog-cartoon-67", version=4)
    existing = project(design=frozen)
    existing.style = "cartoon"
    assert book_design.select(existing, "auto") == frozen
    assert book_design.select(existing, "catalog-cartoon-67") == frozen
    assert book_design.resolve(existing.book_profile) == frozen


@pytest.mark.parametrize("index", sorted(UPDATED | INSERTED))
def test_approved_batch_uses_photography_and_the_rounded_navy_typography(index):
    design = book_design.snapshot(f"catalog-realistic-{index}")
    assert design["version"] == book_design.CURRENT_CATALOG_VERSION
    assert design["visual"]["finish"] == "premium_photographic_editorial_realism"
    assert design["interior"]["mode"] == "two_scenes"
    assert design["interior"]["font_ratio"] == 0.038
    policy = book_design.apply_policy(
        design, editorial_profile.policy({"editorial": editorial_profile.snapshot()})
    )
    assert policy["typography"]["titleFontFile"] == "Nunito-Black.ttf"
    assert policy["typography"]["bodyFontFile"] == "Nunito-Medium.ttf"
    assert policy["typography"]["titleWeight"] == 900
    assert policy["typography"]["baseWeight"] == 500
    assert policy["typography"]["titleColor"] == "#061A45"
    assert policy["typography"]["color"] == "#071337"
    assert policy["typography"]["titleGoldOrnaments"] is True
    assert all(path.endswith("-20261124.webp") for path in design["reference_files"].values())


@pytest.mark.parametrize("language", ["pt-BR", "en", "es"])
def test_new_single_name_title_is_personalized_in_every_locale(language):
    customer = project(name="João", language=language)
    book_design.select(customer, "catalog-realistic-69")
    expected = {
        "pt-BR": "João e as Pegadas de um Gigante",
        "en": "João and the Giant's Footprints",
        "es": "João y las Huellas de un Gigante",
    }
    assert customer.book_profile["title"] == expected[language]
    assert {
        key: value["title"] for key, value in customer.book_profile["supplied_locales"].items()
    } == expected
    assert customer.theme == "Uma história escolhida pela família"


@pytest.mark.parametrize("language", ["pt-BR", "en", "es"])
def test_new_couple_title_replaces_the_whole_localized_name_phrase(language):
    customer = project(language=language)
    design = book_design.select(customer, "catalog-realistic-87")
    assert design["example_names"] == {
        "pt-BR": "Catarina e João",
        "en": "Catarina and João",
        "es": "Catarina y João",
    }
    expected = {
        "pt-BR": "Ana & Pedro: Do Primeiro Olhar ao Nosso Lar",
        "en": "Ana & Pedro: From Our First Glance to Our Home",
        "es": "Ana & Pedro: De la Primera Mirada a Nuestro Hogar",
    }
    assert customer.book_profile["title"] == expected[language]
    assert {
        key: value["title"] for key, value in customer.book_profile["supplied_locales"].items()
    } == expected
    assert book_design.select(customer, "auto") == design


@pytest.mark.parametrize("index", [88, 90])
@pytest.mark.parametrize("language", ["pt-BR", "en", "es"])
def test_generic_couple_and_sibling_titles_are_not_rewritten_with_sample_names(index, language):
    customer = project(language=language)
    selected = book_design.select(customer, f"catalog-realistic-{index}")
    assert len(selected["example_names"]) == 3
    assert customer.book_profile["title"] == selected["title_templates"][language]
    assert "Ana & Pedro" not in customer.book_profile["title"]


def test_explicit_customer_title_survives_new_catalog_selection_and_retry():
    literal = "Ana & Pedro: A Nossa História"
    customer = project(title=literal)
    for choice in ("catalog-realistic-87", "catalog-realistic-87", "auto"):
        book_design.select(customer, choice)
        assert customer.book_profile["title"] == literal
        assert all(
            value["title"] == literal
            for value in customer.book_profile["supplied_locales"].values()
        )


@pytest.mark.parametrize("index", [69, 87, 90, 118])
def test_new_models_do_not_claim_an_unprovided_cartoon_or_v4_edition(index):
    with pytest.raises(HTTPException) as old:
        book_design.snapshot(f"catalog-realistic-{index}", version=4)
    assert old.value.status_code == 400
    with pytest.raises(HTTPException) as cartoon:
        book_design.snapshot(f"catalog-cartoon-{index}", version=5)
    assert cartoon.value.status_code == 400
