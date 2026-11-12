import io

import pytest
from PIL import Image

from app.services import scene_composition


@pytest.mark.parametrize(
    "region,alignment",
    [
        ([0.06, 0.045, 0.94, 0.29], "center"),
        ([0.06, 0.06, 0.94, 0.36], "center"),
        ([0.06, 0.06, 0.94, 0.36], "right"),
        ([0.55, 0.07, 0.94, 0.35], "left"),
        ([0.48, 0.04, 0.94, 0.42], "right"),
    ],
)
def test_diagram_reserves_title_without_overlapping_complete_head(region, alignment):
    raw, geometry = scene_composition.cover_guide(region, alignment=alignment)
    image = Image.open(io.BytesIO(raw))
    assert image.size == (1024, 1024)
    head = geometry["head_envelope"]
    overlap = max(0, min(head[2], region[2]) - max(head[0], region[0])) * max(
        0, min(head[3], region[3]) - max(head[1], region[1])
    )
    assert overlap == 0
    assert head[3] - head[1] <= 0.221
    assert image.getpixel((round((head[0] + head[2]) * 512), round((head[1] + head[3]) * 512))) == (
        98,
        116,
        131,
    )
    assert image.getpixel(
        (round((region[0] + region[2]) * 512), round((region[1] + region[3]) * 512))
    ) == (246, 217, 107)
    assert scene_composition.cover_guide(region, alignment=alignment)[0] == raw


@pytest.mark.parametrize("region", [[0.1, 0.1, 0.1, 0.3], [0, 0, 1, 0.8], [-0.1, 0, 1, 0.3]])
def test_invalid_title_geometry_never_reaches_generation(region):
    with pytest.raises(ValueError):
        scene_composition.cover_guide(region, alignment="center")
