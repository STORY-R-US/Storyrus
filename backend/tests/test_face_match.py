"""Testes do juiz de identidade foto x cena (InsightFace only, sem rede)."""

from io import BytesIO

import pytest
from PIL import Image

from app.ai_clients import face_match as fm


def _png() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (64, 64), (30, 90, 40)).save(buf, format="PNG")
    return buf.getvalue()


def test_coerce_face_score():
    filled = fm.coerce_face_score(fm.FaceScore(match=0.8, eye_inflate=None, geometry=None))
    assert filled is not None
    assert filled.eye_inflate == 0.0
    assert filled.geometry == 0.8
    assert fm.coerce_face_score(0.91).match == 0.91
    assert fm.coerce_face_score(None) is None


def test_identity_accepted_none_does_not_block():
    assert fm.identity_accepted(None) is True
    assert fm.identity_accepted(0.91, min_score=0.72) is True
    assert fm.identity_accepted(0.4, min_score=0.72) is False


def test_match_from_cosine_maps_arcface_range():
    assert fm.match_from_cosine(0.18) == 0.0
    assert fm.match_from_cosine(0.52) == 1.0
    assert 0.4 < fm.match_from_cosine(0.35) < 0.6
    assert fm.match_from_cosine(0.32, domain="same") == 0.0
    assert fm.match_from_cosine(0.62, domain="same") == 1.0
    assert fm.match_from_cosine(0.40, domain="same") < fm.match_from_cosine(0.40)


@pytest.mark.asyncio
async def test_score_face_match_uses_insightface(monkeypatch):
    def fake_score(_photo, _scene, *, domain="photo"):
        return fm.FaceScore(match=0.88, eye_inflate=0.0, geometry=0.88, age=0.88, hair=0.88)

    monkeypatch.setattr(fm, "_score_insightface", fake_score)
    score = await fm.score_face_match(_png(), _png())
    assert score == 0.88


@pytest.mark.asyncio
async def test_score_face_match_none_when_insightface_misses(monkeypatch):
    monkeypatch.setattr(fm, "_score_insightface", lambda *_a, **_k: None)
    assert await fm.score_face_match(_png(), _png()) is None


class _Face:
    def __init__(self, bbox, emb):
        self.bbox = bbox
        self.normed_embedding = emb


def test_pick_embedding_without_probe_uses_largest_bbox():
    small = _Face([0, 0, 10, 10], [1.0, 0.0])
    large = _Face([0, 0, 100, 100], [0.0, 1.0])
    picked = fm._pick_embedding([small, large])
    assert list(picked) == [0.0, 1.0]


def test_pick_embedding_with_probe_uses_closest_not_largest():
    probe = [1.0, 0.0]
    adult = _Face([0, 0, 200, 200], [0.0, 1.0])
    child = _Face([10, 10, 40, 40], [0.99, 0.01])
    picked = fm._pick_embedding([adult, child], probe=probe)
    assert fm._cosine(picked, probe) > fm._cosine(adult.normed_embedding, probe)


def test_pick_embedding_skips_faces_without_embedding():
    empty = _Face([0, 0, 80, 80], None)
    empty.normed_embedding = None
    empty.embedding = None
    only = _Face([0, 0, 20, 20], [0.2, 0.8])
    assert list(fm._pick_embedding([empty, only])) == [0.2, 0.8]
    assert fm._pick_embedding([]) is None


def test_face_boxes_skips_tiny_and_keeps_valid(monkeypatch):
    class _BBox:
        def __init__(self, bbox):
            self.bbox = bbox

    monkeypatch.setattr(
        fm, "_faces_in", lambda _data: [_BBox([0, 0, 4, 4]), _BBox([10, 20, 80, 90])]
    )
    assert fm.face_boxes(b"x") == [(10, 20, 80, 90)]


def test_score_insightface_matches_child_not_larger_adult(monkeypatch):
    crop = _Face([0, 0, 80, 80], [1.0, 0.0])
    adult = _Face([0, 0, 200, 200], [0.0, 1.0])
    child = _Face([10, 10, 40, 40], [0.95, 0.05])

    def fake_faces(data: bytes):
        return [crop] if data == b"photo" else [adult, child]

    monkeypatch.setattr(fm, "_faces_in", fake_faces)
    scored = fm._score_insightface(b"photo", b"scene")
    assert scored is not None
    assert scored.match == 1.0
