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


def test_expansion_preserves_person_pixels_and_never_stretches_source():
    source = Image.new("RGB", (1024, 1024), "red")
    buffer = io.BytesIO()
    source.save(buffer, "PNG")
    seed, mask, transform = scene_composition.expansion_canvas(
        buffer.getvalue(), 0.30, 0.36, protected=[[0, 0, 0.3, 0.4]]
    )
    framed = Image.open(io.BytesIO(seed))
    alpha = Image.open(io.BytesIO(mask)).getchannel("A")
    assert framed.size == (1024, 1024)
    assert transform["top"] > 0.30 * 1024
    assert alpha.getpixel((512, 50)) == 0
    assert alpha.getpixel((transform["left"], transform["top"])) == 255
    generated = Image.new("RGB", (1024, 1024), "blue")
    buffer = io.BytesIO()
    generated.save(buffer, "PNG")
    final = Image.open(
        io.BytesIO(scene_composition.preserve_expansion_core(buffer.getvalue(), seed, mask))
    )
    assert final.getpixel((512, 50)) == (0, 0, 255)
    assert final.getpixel((512, 700)) == (255, 0, 0)
    assert final.getpixel((transform["left"], transform["top"])) == (255, 0, 0)


@pytest.mark.parametrize("bad", ["missing", "duplicate", "invalid", "conflicting"])
def test_crop_reviews_fail_closed_for_partial_or_conflicting_evidence(bad):
    import json

    from app.ai_clients.base import ProviderError
    from app.services import editorial_review

    rows = [{"line": n, "valid": True, "issues": [], "limitations": []} for n in (1, 2)]
    value = {"results": rows}
    if bad == "missing":
        rows.pop()
    if bad == "duplicate":
        rows[1]["line"] = 1
    if bad == "invalid":
        rows[1]["valid"] = "true"
    if bad == "conflicting":
        value["valid"] = True
    with pytest.raises(ProviderError):
        editorial_review.parse_crop_report(json.dumps(value), 2)


def test_crop_reviews_keep_every_rejection_instead_of_approving_the_other_lines():
    import json

    from app.services import editorial_review

    rows = [{"line": n, "valid": True, "issues": [], "limitations": []} for n in range(1, 8)]
    rows[0].update(valid=False, issues=["Visible hair"])
    rows[6].update(valid=False, issues=["Visible face"])
    report = editorial_review.parse_crop_report(json.dumps({"results": rows}), 7)
    assert report["valid"] is False
    assert report["issues"] == ["Line 1: Visible hair", "Line 7: Visible face"]
