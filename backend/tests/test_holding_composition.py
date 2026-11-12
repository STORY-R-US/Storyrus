"""Synthetic product photos only: no provider calls or customer images."""

import io

import cv2
import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageEnhance, ImageOps

from app.services import book_design
from app.workers import editorial_render as render


def folded_fixture(size=600):
    image = Image.new("RGB", (600, 600), "#eeeecc")
    draw = ImageDraw.Draw(image)
    # Two rigid boards, joined at the concave top hinge. Hands hide the
    # lower outer corners, exactly where a hull would join the wrong planes.
    draw.polygon(
        [(120, 160), (340, 210), (540, 170), (450, 450), (280, 500), (65, 440)], fill="#d522bd"
    )
    draw.rectangle((60, 360, 180, 470), fill="#bc9878")
    draw.rectangle((420, 360, 530, 460), fill="#bc9878")
    return image.resize((size, size))


@pytest.mark.parametrize("size", [300, 600, 1024])
def test_folded_book_uses_one_board_and_preserves_every_unmarked_pixel(size):
    image = folded_fixture(size)
    raw = render.encode(image)
    cover = Image.new("RGB", (200, 200), "#77bbdd")
    ImageDraw.Draw(cover).rectangle((0, 0, 90, 90), fill="#dd4422")
    art = render.encode(cover)
    prepared, geometry, masks = render.keyed_folded_cover(raw)
    output, provenance = render.mockup(prepared, [art], geometry, visible_masks=masks)
    result = np.array(Image.open(io.BytesIO(output)))
    original = np.array(image)
    hsv = cv2.cvtColor(original, cv2.COLOR_RGB2HSV)
    marked = cv2.inRange(hsv, (135, 15, 35), (175, 255, 255)) > 0
    assert np.array_equal(result[~marked], original[~marked])
    assert not np.any(np.all(result[marked] == original[marked], axis=1))
    assert geometry["surfaces"][0][0][0] > 0.5  # front starts at the hinge
    assert geometry["surfaces"][0][1][0] > 0.85
    assert provenance["surfaces"][0]["source_sha256"] == render.digest(art)
    # The upper-left source landmark remains upper-left on the RIGHT board.
    assert result[round(size * 0.4), round(size * 0.62), 0] > 150
    assert result[round(size * 0.45), round(size * 0.3), 0] < 40


def test_single_plane_does_not_invent_a_hinge():
    image = Image.new("RGB", (300, 300), "white")
    ImageDraw.Draw(image).rectangle((50, 50, 250, 250), fill="#ff00ff")
    assert render.keyed_folded_cover(render.encode(image)) is None
    assert render.keyed_folded_cover(render.encode(Image.new("RGB", (300, 300), "white"))) is None


@pytest.mark.parametrize(
    "surface,error",
    [
        ([[0.2, 0.4], [0.9, 0.4], [0.9, 0.65], [0.2, 0.65]], "deformada"),
        ([[0.4, 0.3], [0.9, 0.3], [0.9, 0.8], [0.4, 0.8]], "rosa exposta"),
    ],
)
def test_valid_convex_vision_rectangle_is_not_enough(surface, error):
    image = Image.new("RGB", (300, 300), "white")
    ImageDraw.Draw(image).rectangle((30, 60, 280, 270), fill="#ff00ff")
    geometry = {"valid": True, "issues": [], "surfaces": [surface], "occlusions": []}
    with pytest.raises(ValueError, match=error):
        render.mockup(render.encode(image), [render.encode(image)], geometry)


def test_pink_in_finished_art_is_not_registration_leak():
    image = Image.new("RGB", (300, 300), "white")
    ImageDraw.Draw(image).rectangle((50, 50, 250, 250), fill="#ff00ff")
    raw = render.encode(image)
    geometry, masks = render.keyed_surfaces(raw, 1)
    output, _ = render.mockup(
        raw, [render.encode(Image.new("RGB", (300, 300), "#ff00ff"))], geometry, visible_masks=masks
    )
    assert output


@pytest.mark.parametrize("angle", [-20, -12, 0, 12, 20])
@pytest.mark.parametrize("light", [0.4, 0.7, 1.0])
@pytest.mark.parametrize(
    "skin,accessory",
    [
        ("#e9b892", "curly_hair"),
        ("#8b5137", "long_hair"),
        ("#bd835f", "blue_hat"),
        ("#f0cdb0", "pink_bow"),
    ],
)
def test_local_children_lighting_and_tilt_keep_identity_pixels(angle, light, skin, accessory):
    image = folded_fixture()
    draw = ImageDraw.Draw(image)
    draw.ellipse((240, 25, 340, 125), fill=skin)
    if accessory in {"curly_hair", "long_hair"}:
        for x in range(230, 350, 15):
            draw.ellipse((x, 15, x + 25, 50 if accessory == "curly_hair" else 140), fill="#342019")
    else:
        draw.rectangle((230, 15, 350, 48), fill="#176399" if accessory == "blue_hat" else "#e528c1")
    image = ImageEnhance.Brightness(image).enhance(light).rotate(angle, fillcolor="#eeeecc")
    raw = render.encode(image)
    prepared, geometry, masks = render.keyed_folded_cover(raw)
    out, _ = render.mockup(
        prepared,
        [render.encode(Image.new("RGB", (300, 300), "#55aacc"))],
        geometry,
        visible_masks=masks,
    )
    result = np.array(Image.open(io.BytesIO(out)))
    original = np.array(image)
    identity = Image.new("L", (600, 600))
    ImageDraw.Draw(identity).rectangle((225, 0, 380, 145), fill=255)
    protected = np.array(identity.rotate(angle)) > 0
    assert np.array_equal(result[protected], original[protected])
    assert masks[0].any()


@pytest.mark.parametrize("model", list(book_design.definitions(4)["models"]))
@pytest.mark.parametrize("angle", [-12, 0, 12])
def test_saved_catalog_covers_keep_their_pixels_and_orientation(model, angle):
    design = book_design.snapshot(model)
    reference = Image.open(io.BytesIO(book_design.reference(design, "cover"))).convert("RGB")
    # Some catalog references are photographs of a book, not printable square
    # art. Put the ENTIRE reference on a local test canvas without cropping or
    # stretching. This is a test fixture, never a replacement production cover.
    contained = ImageOps.contain(reference, (512, 512))
    canvas = Image.new("RGB", (512, 512), "white")
    canvas.paste(contained, ((512 - contained.width) // 2, (512 - contained.height) // 2))
    art = render.encode(canvas)
    raw = render.encode(folded_fixture(300).rotate(angle, fillcolor="#eeeecc"))
    prepared, geometry, masks = render.keyed_folded_cover(raw)
    output, meta = render.mockup(prepared, [art], geometry, visible_masks=masks)
    result = np.array(Image.open(io.BytesIO(output)))
    source = np.array(render.square(art))
    # Independently project the saved cover, then compare with illumination
    # tolerance. This catches mirrored titles, wrong catalog art and lost detail.
    matrix = np.array(meta["surfaces"][0]["matrix"])
    expected = cv2.warpPerspective(
        source, matrix, (300, 300), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )
    inside = cv2.erode(masks[0], np.ones((5, 5), np.uint8)) > 0
    assert np.mean(np.abs(result[inside].astype(float) - expected[inside])) < 18
    assert meta["surfaces"][0]["source_sha256"] == render.digest(art)
    assert book_design.resolve({"book_design": design}) == design


def test_larger_pink_background_does_not_replace_child_or_hide_book():
    image = Image.new("RGB", (600, 950), "#eeeecc")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 599, 320), fill="#d522bd")
    draw.ellipse((230, 30, 370, 240), fill="#ae7855")
    image.paste(folded_fixture(), (0, 350))
    prepared, geometry, masks = render.keyed_folded_cover(render.encode(image))
    out, _ = render.mockup(
        prepared,
        [render.encode(Image.new("RGB", (300, 300), "blue"))],
        geometry,
        visible_masks=masks,
    )
    assert (
        Image.open(io.BytesIO(out)).crop((0, 0, 600, 350)).tobytes()
        == image.crop((0, 0, 600, 350)).tobytes()
    )


def test_rectangle_missing_the_book_cannot_silently_pass():
    image = Image.new("RGB", (600, 600), "white")
    ImageDraw.Draw(image).rectangle((330, 330, 560, 560), fill="#ff00ff")
    geometry = {
        "valid": True,
        "issues": [],
        "occlusions": [],
        "surfaces": [[[0.05, 0.05], [0.45, 0.05], [0.45, 0.45], [0.05, 0.45]]],
    }
    with pytest.raises(ValueError, match="não coincide"):
        render.mockup(render.encode(image), [render.encode(image)], geometry)


def test_two_marked_books_need_explicit_geometry_instead_of_guessing():
    image = Image.new("RGB", (1200, 600), "white")
    image.paste(folded_fixture(), (0, 0))
    image.paste(folded_fixture(), (600, 0))
    with pytest.raises(ValueError, match="Mais de um livro"):
        render.keyed_folded_cover(render.encode(image))
