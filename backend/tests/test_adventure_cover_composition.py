import io

import pytest
from PIL import Image, ImageChops

from app.services import book_design, editorial_profile
from app.workers import editorial_render as render


@pytest.mark.parametrize(
    "title",
    [
        "João Descobre o Mar Azul",
        "Beatriz Explora o Jardim",
        "Sofia Explores the Ocean",
        "Mateo Descubre el Mar",
    ],
)
def test_new_cover_balances_other_children_without_altering_scenery(title):
    profile = {
        "editorial": editorial_profile.snapshot(),
        "book_design": book_design.snapshot("adventure"),
    }
    # Distinct pixels make side stretching or background replacement observable.
    image = Image.new("RGB", (1024, 1024))
    image.putdata(
        [
            (110 + x % 100, 160 + y % 80, 200 + (x + y) % 50)
            for y in range(1024)
            for x in range(1024)
        ]
    )
    raw = render.encode(image)
    data, layout = render.text(raw, title, profile, title=True)
    assert " ".join(layout["lines"]) == title
    assert len(layout["lines"]) == 2
    assert layout["font_size"] >= 90
    assert layout["gold_ornaments"] > 0
    actual = Image.open(io.BytesIO(data)).convert("RGB")
    difference = ImageChops.difference(image, actual)
    assert difference.getbbox()[3] < 350
    # Entire child area and both side margins retain the input pixels exactly.
    for box in [(0, 350, 1024, 1024), (0, 0, 50, 1024), (974, 0, 1024, 1024)]:
        assert difference.crop(box).getbbox() is None
    _, measured = render.text(raw, title, profile, title=True, measure_only=True)
    assert measured["ink_regions_with_margin"] == layout["ink_regions_with_margin"]
    assert measured["gold_ornaments"] == layout["gold_ornaments"]


def test_title_repair_cannot_move_into_a_corner_or_over_a_hat():
    profile = {
        "editorial": editorial_profile.snapshot(),
        "book_design": book_design.snapshot("adventure"),
    }
    raw = render.encode(Image.new("RGB", (1024, 1024), "skyblue"))
    with pytest.raises(render.TextLayoutError):
        render.reading_region_candidates(
            raw,
            "Beatriz Explora o Jardim",
            profile,
            [0.06, 0.06, 0.94, 0.29],
            title=True,
            obstacles=[[0.1, 0, 0.9, 0.4]],
            suggested=[0.56, 0.45, 0.94, 0.8],
        )


def test_cover_direction_is_generic_and_does_not_change_interior_framing():
    design = book_design.snapshot("adventure")
    for action in ("Beatriz observa flores", "Mateo procura conchas"):
        prompt = book_design.prompt(design, "cover", action)
        assert action in prompt
        assert "No stretched side strips" in prompt
        assert "foreground, middle ground and background" in prompt
        assert "below the title reserve" in prompt
    assert "Plan the complete environment" not in book_design.prompt(design, "page", "Lia lê")


@pytest.mark.parametrize("version", [1, 2])
def test_frozen_covers_keep_their_original_layout_without_gold(version):
    profile = {
        "editorial": editorial_profile.snapshot(),
        "book_design": book_design.snapshot("adventure", version=version),
    }
    _, layout = render.text(
        render.encode(Image.new("RGB", (1024, 1024), "skyblue")), "Outro Nome", profile, title=True
    )
    assert layout["gold_ornaments"] == 0
