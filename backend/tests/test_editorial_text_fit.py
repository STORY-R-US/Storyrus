import io
import unicodedata

import pytest
from PIL import Image

from app.services import book_design, editorial_profile
from app.workers import editorial_render as render


def blank():
    return render.encode(Image.new("RGB", (1024, 1024), "#fff8ec"))


@pytest.mark.parametrize("model", ["family", "adventure", "cartoon", None])
@pytest.mark.parametrize(
    "title",
    [
        "João Pedro e suas extraordinárias descobertas no parque",
        "Amor de Bisavó: Matteo e sua família em uma aventura inesquecível",
        "Aventuras extraordinarias de Sebastián y su mejor amigo",
        "Christopher and his extraordinary adventures with Grandma",
        "André no computador",
        "Meu pai, meu herói!",
    ],
)
def test_catalog_titles_fit_without_rewriting_or_moving_the_design(model, title):
    profile = {"editorial": editorial_profile.snapshot()}
    if model:
        profile["book_design"] = book_design.snapshot(model)
    source = blank()
    region = editorial_profile.policy(profile)["referenceComposition"]["coverRegion"]
    _, layout = render.text(source, title, profile, title=True)
    assert layout["text"] == title
    assert " ".join(layout["lines"]) == title
    assert layout["region"] == region
    assert layout["font_size"] >= layout["minimum_font_size"] >= 35
    assert layout["ink_region_with_margin"][3] <= region[3] + 0.015
    # Measuring and actual composition must choose exactly the same fit.
    measured, evidence = render.text(source, title, profile, title=True, measure_only=True)
    assert measured == source and evidence == layout


def test_fitting_is_local_keeps_copy_and_handles_decomposed_accents():
    profile = {
        "editorial": editorial_profile.snapshot(),
        "book_design": book_design.snapshot("family"),
    }
    literal = "João Pedro e suas extraordinárias descobertas no parque"
    _, layout = render.text(blank(), literal, profile, title=True)
    assert layout["fit_adjusted"]
    decomposed = unicodedata.normalize("NFD", "João e André")
    _, accents = render.text(blank(), decomposed, profile, title=True)
    assert accents["text"] == decomposed
    assert " ".join(accents["lines"]) == "João e André"


@pytest.mark.parametrize("model", ["family", "adventure", "cartoon"])
def test_long_body_copy_stays_readable_and_extreme_copy_has_actionable_error(model):
    profile = {
        "editorial": editorial_profile.snapshot(),
        "book_design": book_design.snapshot(model),
    }
    literal = "\n".join(
        [
            "João Pedro descobre novos caminhos pelo parque,",
            "com alegria e carinho aprende a observar.",
            "Cada folha conta uma história diferente,",
            "e a amizade faz o seu sorriso despertar.",
        ]
    )
    output, layout = render.text(blank(), literal, profile, readable=True)
    assert layout["text"] == literal
    assert layout["font_size"] >= 28
    assert Image.open(io.BytesIO(output)).size == (1024, 1024)
    with pytest.raises(render.TextLayoutError, match="Encurte"):
        render.text(blank(), "Texto extenso. " * 500, profile)
