import io

import numpy as np
import pytest
from PIL import Image, ImageDraw

from app.workers import editorial_render as render
from app.workers import local_scene_details as details


def scene(size=512):
    image = Image.new("RGB", (size, size), "#a5d5ee")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, round(size * 0.65), size, size), fill="#4e8a45")
    draw.ellipse(
        (round(size * 0.35), round(size * 0.4), round(size * 0.55), round(size * 0.6)),
        fill="#b58261",
    )
    return image


@pytest.mark.parametrize("size", [256, 512, 1024])
@pytest.mark.parametrize(
    "head", [[0.30, 0.32, 0.62, 0.95], [0.02, 0.32, 0.40, 0.95], [0.60, 0.32, 0.98, 0.95]]
)
def test_details_preserve_faces_text_pixels_and_source_dimensions(size, head):
    original = scene(size)
    raw = render.encode(original)
    protected = [head, [0, 0, 1, 0.30]]
    out, report = details.enrich(raw, theme="futebol", protected=protected)
    result = Image.open(io.BytesIO(out))
    assert result.size == original.size
    assert report["provider_calls"] == 0 and report["added"]
    for box in protected:
        pixels = tuple(round(v * size) for v in box)
        assert result.crop(pixels).tobytes() == original.crop(pixels).tobytes()
    assert details.enrich(raw, theme="futebol", protected=protected)[0] == out
    assert all(0 <= v <= 1 for item in report["added"] for v in item["region"])


@pytest.mark.parametrize(
    "theme,protected",
    [("bale", [[0.3, 0.3, 0.7, 0.9]]), ("futebol", []), ("futebol", [[0, 0, 1, 1]])],
)
def test_unknown_theme_missing_map_and_full_occlusion_keep_saved_art(theme, protected):
    raw = render.encode(scene())
    out, report = details.enrich(raw, theme=theme, protected=protected)
    assert out == raw and not report["added"]


@pytest.mark.parametrize(
    "box", [[0, 0, float("nan"), 1], [-1, 0, 1, 1], [0.8, 0.2, 0.3, 0.9], [0, 0, 1]]
)
def test_invalid_obstacles_fail_without_a_new_image(box):
    with pytest.raises(ValueError):
        details.enrich(render.encode(scene()), theme="futebol", protected=[box])


def test_indoor_scene_does_not_receive_a_stadium():
    raw = render.encode(Image.new("RGB", (512, 512), "#bbae96"))
    out, report = details.enrich(raw, theme="futebol", protected=[[0.3, 0.2, 0.8, 0.9]])
    assert out == raw and report["reason"] == "field_not_identified"


def test_framed_saved_landscape_changes_only_approved_wall_rectangle():
    original = Image.new("RGB", (512, 512), "#8b8175")
    raw = render.encode(original)
    region = [0.03, 0.1, 0.27, 0.3]
    out = details.framed_scene(
        raw, render.encode(scene()), region=region, protected=[[0.35, 0, 0.8, 1]]
    )
    result = np.array(Image.open(io.BytesIO(out)))
    source = np.array(original)
    mask = np.zeros((512, 512), bool)
    mask[round(0.1 * 512) : round(0.3 * 512), round(0.03 * 512) : round(0.27 * 512)] = True
    assert np.array_equal(result[~mask], source[~mask])
    assert not np.array_equal(result[mask], source[mask])
    with pytest.raises(ValueError, match="overlaps"):
        details.framed_scene(raw, raw, region=region, protected=[[0.1, 0.1, 0.9, 0.9]])
