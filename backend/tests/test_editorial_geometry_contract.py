"""Adversarial book layouts, with locally drawn fixtures and no external services."""

import json

import pytest
from PIL import Image, ImageDraw

from app.ai_clients.base import ProviderError
from app.services import editorial_profile, editorial_review
from app.workers import editorial_render as render


@pytest.mark.parametrize("side", ["left", "right"])
@pytest.mark.parametrize("hat_top", [0.0, 0.06, 0.15])
@pytest.mark.parametrize("literal", ["André no parque", "Um dia de descobertas\ncom André"])
def test_title_search_protects_whole_face_and_blue_knit_hat(monkeypatch, side, hat_top, literal):
    profile = {"editorial": editorial_profile.snapshot("2026-11-05.3")}
    x0, x1 = (0.05, 0.53) if side == "left" else (0.47, 0.95)
    source = Image.new("RGB", (1024, 1024), "#bfe3ef")
    draw = ImageDraw.Draw(source)
    draw.rectangle((x0 * 1024, hat_top * 1024, x1 * 1024, 0.35 * 1024), fill="#125895")
    draw.rectangle((x0 * 1024, 0.35 * 1024, x1 * 1024, 0.65 * 1024), fill="#d9a078")
    raw = render.encode(source)
    # A covered/profile face can be missed by the local detector. The observed
    # whole-scene map must still protect ALL pixels of the hat and face.
    monkeypatch.setattr(render, "protected_heads", lambda _: [])
    protected = render.protected_regions(
        [
            {"kind": "head", "region": [x0, hat_top, x1, 0.65]},
            {"kind": "hat", "region": [x0, hat_top, x1, 0.35]},
            {"kind": "action", "region": [0.05, 0.7, 0.95, 0.95]},
        ]
    )
    choices = render.reading_region_candidates(
        raw, literal, profile, [0.06, 0.055, 0.94, 0.31], title=True, obstacles=protected
    )
    for region in choices:
        output, layout = render.text(raw, literal, profile, title=True, region=region)
        assert not render.layout_overlaps(layout, protected)
        assert layout["text"] == literal
        assert layout["font_size"] >= layout["minimum_font_size"]
        box = tuple(round(v * 1024) for v in [x0, hat_top, x1, 0.65])
        assert render.square(output).crop(box).tobytes() == source.crop(box).tobytes()


def test_face_between_line_bounds_is_not_text_overlap():
    profile = {"editorial": editorial_profile.snapshot("2026-11-05.3")}
    raw = render.encode(Image.new("RGB", (1024, 1024), "#bfe3ef"))
    _, layout = render.text(
        raw, "UMA GRANDE AVENTURA\nLia", profile, title=True, region=[0.06, 0.055, 0.94, 0.4]
    )
    first = layout["ink_regions_with_margin"][0]
    second = layout["ink_regions_with_margin"][-1]
    # Below the wide first line and beside the short second line: the old
    # enclosing rectangle falsely treated this unused space as title ink.
    top = max(line[3] for line in layout["ink_regions_with_margin"][:-1]) + 0.001
    box = [first[0], top, second[0] - 0.015, second[3]]
    assert render._intersection(layout["ink_region_with_margin"], box) > 0
    assert not render.layout_overlaps(layout, [box])


def test_no_safe_space_is_an_actionable_local_failure(monkeypatch):
    profile = {"editorial": editorial_profile.snapshot("2026-11-05.3")}
    raw = render.encode(Image.new("RGB", (128, 128), "#bfe3ef"))
    monkeypatch.setattr(render, "protected_heads", lambda _: [])
    with pytest.raises(render.TextLayoutError, match="não cabe"):
        render.reading_region_candidates(
            raw, "Meu herói", profile, [0.06, 0.06, 0.94, 0.3], title=True, obstacles=[[0, 0, 1, 1]]
        )


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        [{"kind": "hat", "region": [True, 0, 1, 1]}],
        [{"kind": "hat", "region": [0, 0, float("nan"), 1]}],
        [{"kind": "hat", "region": [0, 0, 2, 1]}],
        [{"kind": "hat", "region": [0.7, 0, 0.2, 1]}],
        [{"kind": "text", "region": [0, 0, 1, 1]}],
        [{"kind": [], "region": [0, 0, 1, 1]}],
        [{"kind": {}, "region": [0, 0, 1, 1]}],
    ],
)
def test_invalid_protection_map_never_becomes_clearance(value):
    with pytest.raises(render.TextLayoutError):
        render.protected_regions(value)


@pytest.mark.parametrize("lines", [[], [None], [[0, 0, float("nan"), 1]], [[0, 0, 2, 1]]])
def test_invalid_ink_geometry_cannot_pass_protected_area_check(lines):
    with pytest.raises(render.TextLayoutError):
        render.layout_overlaps({"ink_regions_with_margin": lines}, [[0.3, 0, 0.7, 0.6]])


def test_line_geometry_does_not_require_an_enclosing_rectangle():
    layout = {"ink_regions_with_margin": [[0.1, 0.1, 0.9, 0.2]]}
    assert render.layout_overlaps(layout, [[0.3, 0, 0.7, 0.6]])
    assert not render.layout_overlaps(layout, [[0.3, 0.3, 0.7, 0.6]])


@pytest.mark.parametrize("kind", ["hair", "hat", "accessory"])
@pytest.mark.parametrize("side", ["left", "right", "both"])
def test_hair_accessories_profiles_and_multiple_people_keep_original_pixels(
    monkeypatch, kind, side
):
    profile = {"editorial": editorial_profile.snapshot("2026-11-05.3")}
    source = Image.new("RGB", (512, 512), "#bfe3ef")
    draw = ImageDraw.Draw(source)
    # Hair / a bow / a broad hat extends beyond the narrow profile-face box.
    regions = []
    for edge in ["left", "right"] if side == "both" else [side]:
        x0, x1 = (0.01, 0.25) if edge == "left" else (0.75, 0.99)
        regions.extend(
            [
                {"kind": "head", "region": [x0, 0.12, x1, 0.65]},
                {"kind": kind, "region": [x0, 0.02, x1, 0.3]},
            ]
        )
    for item in regions:
        draw.rectangle(tuple(round(v * 512) for v in item["region"]), fill="#364370")
    raw = render.encode(source)
    monkeypatch.setattr(render, "protected_heads", lambda _: [])
    protected = render.protected_regions(regions)
    choices = render.reading_region_candidates(
        raw, "Lia e o mar", profile, [0.06, 0.055, 0.94, 0.31], title=True, obstacles=protected
    )
    for region in choices:
        output, layout = render.text(raw, "Lia e o mar", profile, title=True, region=region)
        assert not render.layout_overlaps(layout, protected)
        for item in regions:
            box = tuple(round(v * 512) for v in item["region"])
            assert render.square(output).crop(box).tobytes() == source.crop(box).tobytes()


@pytest.mark.parametrize(
    "value",
    [
        None,
        "null",
        "[]",
        "not JSON",
        json.dumps({"valid": 1, "issues": [], "limitations": []}),
        json.dumps({"valid": True, "issues": [{}], "limitations": []}),
        json.dumps({"valid": False, "issues": [], "limitations": "unknown"}),
        json.dumps({"valid": False, "issues": ["hat"], "limitations": [], "issue_codes": [{}]}),
    ],
)
def test_malformed_review_is_not_approval(value):
    with pytest.raises(ProviderError, match="BOOK_REVIEW_INVALID"):
        editorial_review.parse_report(value)


@pytest.mark.parametrize(
    "code",
    [
        "IDENTITY",
        "ANATOMY",
        "STYLE",
        "SCENE",
        "COLLAGE",
        "GEOMETRY",
        "TEXT_INVALID",
        "INCONCLUSIVE",
    ],
)
def test_non_layout_failure_cannot_be_reclassified_as_overlap(code):
    report = editorial_review.parse_report(
        json.dumps({"valid": False, "issues": ["defect"], "limitations": [], "issue_codes": [code]})
    )
    assert not editorial_review.approved(report)
    assert not editorial_review.overlap_only(report)


def test_only_pure_structured_overlap_allows_text_repair():
    good = {
        "valid": False,
        "issues": ["hat under text"],
        "limitations": [],
        "issue_codes": ["TEXT_OVERLAP"],
    }
    assert editorial_review.overlap_only(good)
    mixed = {
        **good,
        "issues": ["hat under text", "wrong face"],
        "issue_codes": ["TEXT_OVERLAP", "IDENTITY"],
    }
    assert not editorial_review.overlap_only(mixed)


@pytest.mark.parametrize("background,adjusted", [("#bfe3ef", False), ("#071337", True)])
def test_contrast_adjustment_changes_only_literal_ink(background, adjusted):
    profile = {"editorial": editorial_profile.snapshot("2026-11-05.3")}
    original = Image.new("RGB", (512, 512), background)
    raw = render.encode(original)
    output, layout = render.text(raw, "Meu herói", profile, title=True)
    assert layout["contrast_adjusted"] is adjusted
    assert layout["ink_contrast_p15"] >= 3
    assert layout["text"] == "Meu herói"
    assert (
        render.square(output).crop((0, 300, 512, 512)).tobytes()
        == original.crop((0, 300, 512, 512)).tobytes()
    )


@pytest.mark.parametrize("kind", ["JPEG", "WEBP", "PNG"])
def test_valid_provider_image_normalizes_to_png_without_changing_decoded_pixels(kind):
    import io

    image = Image.new("RGB", (128, 128), "#bfe3ef")
    data = io.BytesIO()
    image.save(data, kind)
    raw = data.getvalue()
    normalized = render.normalize_art(raw)
    assert normalized.startswith(b"\x89PNG\r\n\x1a\n")
    assert render.square(normalized).tobytes() == render.square(raw).tobytes()


@pytest.mark.parametrize(
    "plural,singular",
    [
        ("heads", "head"),
        ("faces", "face"),
        ("hairs", "hair"),
        ("hats", "hat"),
        ("hands", "hand"),
        ("bodies", "body"),
        ("accessories", "accessory"),
        ("objects", "object"),
        ("actions", "action"),
    ],
)
def test_equivalent_plural_labels_preserve_all_protection_coordinates(plural, singular):
    source = [{"kind": plural, "region": [0.1, 0.2, 0.4, 0.6]}]
    normalized = render.normalize_protected_regions(source)
    assert normalized == [{"kind": singular, "region": [0.1, 0.2, 0.4, 0.6]}]
    assert source[0]["kind"] == plural
    assert render.protected_regions(source) == render.protected_regions(normalized)


@pytest.mark.parametrize("kind", ["unknown", "hands and face", "", None, ["hand"]])
def test_normalizing_labels_never_ignores_unrecognized_regions(kind):
    with pytest.raises(render.TextLayoutError):
        render.normalize_protected_regions([{"kind": kind, "region": [0.1, 0.2, 0.4, 0.6]}])
