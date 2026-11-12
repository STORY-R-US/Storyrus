"""Synthetic product photos only: no provider calls or customer images."""

import io

import cv2
import numpy as np
import pytest
from PIL import Image, ImageDraw

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
