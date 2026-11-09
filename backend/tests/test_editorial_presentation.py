"""Local presentation changes must preserve copy, source art and foreground hands."""

import io

import pytest
from PIL import Image, ImageDraw

from app.services import editorial_profile
from app.workers import editorial_render as render


@pytest.mark.parametrize("head", [[0.3, 0.06, 0.7, 0.55], [0.3, 0.2, 0.7, 0.6]])
def test_title_rejects_face_hair_or_hat_inside_measured_ink(monkeypatch, head):
    monkeypatch.setattr(render, "protected_heads", lambda _: [head])
    with pytest.raises(ValueError, match="Região do título invade"):
        render.require_clear_title_area(b"art", {"ink_region_with_margin": [0.1, 0.05, 0.9, 0.24]})


def test_title_accepts_head_below_actual_letters_even_inside_larger_plan_region(monkeypatch):
    head = [0.3, 0.27, 0.7, 0.7]
    monkeypatch.setattr(render, "protected_heads", lambda _: [head])
    proof = render.require_clear_title_area(
        b"art",
        {"ink_region_with_margin": [0.1, 0.05, 0.9, 0.24], "region": [0.06, 0.045, 0.94, 0.29]},
    )
    assert proof["protected_heads"] == [head]


def test_reading_area_moves_around_hat_without_rewriting_or_shrinking(monkeypatch):
    profile = {"editorial": editorial_profile.snapshot("2026-11-05.3")}
    source = render.encode(Image.new("RGB", (1000, 1000), "#c3d3b1"))
    literal = "Ele encontra folhas secas\nespalhadas pelo chão.\nPula, gira e inventa\num desenho com a mão."
    monkeypatch.setattr(render, "protected_heads", lambda _: [[0.48, 0.08, 0.94, 0.62]])
    region, evidence = render.choose_reading_region(
        source, literal, profile, [0.09, 0.055, 0.91, 0.31]
    )
    page, layout = render.text(source, literal, profile, region=region, readable=True)
    assert evidence["relocated"] and not evidence["unresolved_head_overlap"]
    assert layout["text"] == literal
    assert layout["font_size"] == 43 and layout["readability_outline"]
    # Moving typography never recolors the protected face/hat pixels.
    original = Image.open(io.BytesIO(source))
    result = Image.open(io.BytesIO(page))
    assert (
        result.crop((480, 80, 940, 620)).tobytes() == original.crop((480, 80, 940, 620)).tobytes()
    )


def test_front_spine_inherits_cover_color_and_preserves_flat_source():
    profile = {"editorial": editorial_profile.snapshot("2026-11-05.3")}
    source = render.encode(Image.new("RGB", (1000, 1000), (30, 140, 190)))
    before = render.digest(source)
    result = Image.open(io.BytesIO(render.front(source, profile=profile)))
    # The rounded spine rolls through the cover's own blue rather than beige.
    for x in (6, 12, 20):
        r, g, b = result.getpixel((x, 500))
        assert b > g > r
    assert render.digest(source) == before
    assert result.getpixel((500, 500)) == (30, 140, 190)


def test_held_book_finish_preserves_hands_and_removes_key_fringe():
    base = Image.new("RGB", (300, 300), (30, 40, 50))
    draw = ImageDraw.Draw(base)
    draw.rectangle((50, 50, 250, 250), fill="#ff00ff")
    draw.line((49, 60, 49, 230), fill="#ffe6ff", width=1)
    draw.rectangle((45, 150, 75, 190), fill=(180, 130, 100))
    raw = render.encode(base)
    geometry, masks = render.keyed_surfaces(raw, 1)
    art = render.encode(Image.new("RGB", (300, 300), (40, 150, 190)))
    output, proof = render.mockup(raw, [art], geometry, visible_masks=masks, physical_book=True)
    result = Image.open(io.BytesIO(output))
    assert result.getpixel((60, 170)) == (180, 130, 100)
    assert result.getpixel((49, 100)) != (255, 230, 255)
    assert proof["binding_finish"] == "cover_derived_hinge"
    assert proof["surfaces"][0]["source_sha256"] == render.digest(art)
    assert result.getpixel((5, 5)) == base.getpixel((5, 5))


def test_overflow_still_preserves_copy_and_font():
    profile = {"editorial": editorial_profile.snapshot("2026-11-05.3")}
    source = render.encode(Image.new("RGB", (1000, 1000), "white"))
    with pytest.raises(ValueError, match="não cabe"):
        render.text(source, "Texto literal muito longo. " * 400, profile, readable=True)


@pytest.mark.parametrize(
    "style,theme,expected",
    [
        ("realistic", "João no parque", "adventure"),
        ("realistic", "Amor de Bisavó", "family"),
        ("realistic", "André no computador", "creative"),
        ("cartoon", "Amor de Mãe", "cartoon"),
    ],
)
def test_catalog_patterns_preserve_requested_style(style, theme, expected):
    from app.services import visual_reference

    assert visual_reference.catalog_family(style, theme) == expected
    if expected != "creative":
        for stage in ("cover", "page", "holding"):
            data = visual_reference.load(stage, style, theme)
            Image.open(io.BytesIO(data)).verify()
