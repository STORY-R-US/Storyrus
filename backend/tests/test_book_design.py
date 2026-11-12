import copy
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services import book_design


@pytest.mark.parametrize("model", ["family", "adventure", "cartoon"])
def test_design_freezes_one_complete_catalog_trio(model):
    design = book_design.snapshot(model)
    assert set(design["reference_sha256"]) == {"cover", "page", "holding"}
    assert book_design.resolve({"book_design": design}) == design
    changed = copy.deepcopy(design)
    changed["cover"]["region"][0] += 0.01
    with pytest.raises(HTTPException) as error:
        book_design.resolve({"book_design": changed})
    assert error.value.status_code == 409


def test_auto_keeps_the_selected_book_when_theme_changes():
    design = book_design.snapshot("family")
    project = SimpleNamespace(
        book_profile={"book_design": design}, style="realistic", theme="Aventura espacial"
    )
    assert book_design.select(project, "auto") == design
    with pytest.raises(HTTPException) as error:
        book_design.select(project, "cartoon")
    assert error.value.status_code == 400


@pytest.mark.parametrize("theme", ["André no computador", "Amor em família", "Aventura espacial"])
def test_new_realistic_books_use_the_meu_pai_heroi_standard_for_every_theme(theme):
    project = SimpleNamespace(book_profile={}, style="realistic", theme=theme)
    selected = book_design.select(project, "auto")
    assert selected["id"] == "adventure"
    assert selected["version"] == 3
    assert selected["visual"]["finish"] == "premium_photographic_editorial_realism"
    assert book_design.preview_interior(selected)["alignment"] == "left"


@pytest.mark.parametrize("version", [1, 2])
def test_existing_frozen_adventure_design_still_resolves_without_migration(version):
    original = book_design.snapshot("adventure", version=version)
    assert book_design.resolve({"book_design": original}) == original
    assert original != book_design.snapshot("adventure")
    project = SimpleNamespace(
        book_profile={"book_design": original}, style="realistic", theme="new"
    )
    assert book_design.select(project, "auto") == original


def test_new_quality_policy_uses_realistic_light_and_local_navy_typography():
    from app.services import editorial_profile

    design = book_design.snapshot("adventure")
    profile = {"editorial": editorial_profile.snapshot(), "book_design": design}
    policy = editorial_profile.policy(profile)
    assert policy["typography"]["titleColor"] == "#061A45"
    assert policy["typography"]["color"] == "#071337"
    assert policy["typography"]["titleFontFile"] == "Nunito-Black.ttf"
    assert "photographic editorial realism" in policy["visual"]["artDirection"]
    prompt = book_design.prompt(design, "preview_page", "André desenha uma flor")
    assert "André desenha uma flor" in prompt
    assert "left-aligned" in prompt
    assert "never copy the example father" in prompt


@pytest.mark.parametrize(
    "title", ["Meu Pai, Meu Herói!", "My Dad, My Hero!", "¡Mi Papá, Mi Héroe!"]
)
def test_reference_titles_fit_safe_margins_before_any_generation(title):
    import io

    from PIL import Image

    from app.services import editorial_profile
    from app.workers import editorial_render

    raw = io.BytesIO()
    Image.new("RGB", (1024, 1024), "skyblue").save(raw, "PNG")
    profile = {
        "editorial": editorial_profile.snapshot(),
        "book_design": book_design.snapshot("adventure"),
    }
    _, layout = editorial_render.text(raw.getvalue(), title, profile, title=True)
    assert layout["text"] == title
    assert layout["weight"] == 900
    assert layout["ink_region_with_margin"][1] >= 0.04


@pytest.mark.parametrize("model", ["family", "cartoon", "adventure"])
def test_all_sixteen_literal_passages_appear_once_in_catalog_layout(model):
    design = book_design.snapshot(model)
    passages = [f"Verso literal número {i:02d}." for i in range(1, 17)]
    result = [book_design.pair_content(design, n, passages) for n in range(1, 17)]
    combined = "\n".join(text for _, text, _ in result)
    for passage in passages:
        assert combined.count(passage) == 1
    if model != "adventure":
        assert sum(role == "illustration" and not text for role, text, _ in result) == 8
        assert result[0][0] == ("reading" if model == "family" else "illustration")
