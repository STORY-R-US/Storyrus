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
