"""Lock de identidade: character_ref obrigatorio e juiz fail-closed."""

import pytest

from app.ai_clients.base import ProviderError
from app.ai_clients.face_match import FaceScore
from app.ai_clients.identity_lock import (
    IDENTITY_REQUIRED_ERROR,
    FaceVerdict,
    build_identity_lock,
    identity_geometry_ok,
    judge_identity,
    prefer_verdict,
    require_character_ref,
    verdict_reason,
)


def _ok(**kw) -> FaceVerdict:
    defaults = dict(eye_inflate=0.05, geometry=0.9, age=0.9, hair=0.9)
    defaults.update(kw)
    return FaceVerdict("scored", defaults.pop("score", 0.88), **defaults)


def test_require_character_ref_rejects_empty():
    with pytest.raises(ProviderError, match="character_ref"):
        require_character_ref(None)
    with pytest.raises(ProviderError, match="character_ref"):
        require_character_ref(b"")
    assert require_character_ref(b"AVATAR") == b"AVATAR"


def test_build_identity_lock_requires_character_ref():
    with pytest.raises(ProviderError, match="obrigatoria"):
        build_identity_lock(character_ref=None, face_crop=b"face")
    lock = build_identity_lock(character_ref=b"AVATAR", face_crop=b"CROP", photo=b"PHOTO")
    assert lock.scene_kwargs() == {"character_ref": b"AVATAR", "photo": b"CROP"}
    assert lock.face_truth == b"CROP"


def test_scene_kwargs_use_photo_when_crop_missing():
    lock = build_identity_lock(character_ref=b"AVATAR", photo=b"PHOTO")
    assert lock.scene_kwargs()["photo"] == b"PHOTO"


def test_face_verdict_fail_closed_on_none():
    threshold = 0.72
    assert FaceVerdict("disabled").accepted(threshold) is True
    assert FaceVerdict("unverified").accepted(threshold) is False
    assert FaceVerdict("scored", None).accepted(threshold) is False
    assert FaceVerdict("scored", 0.4).accepted(threshold) is False
    assert FaceVerdict("scored", 0.72).accepted(threshold) is False  # sem geometria
    assert _ok(score=0.72).accepted(threshold) is True


def test_enlarged_eyes_fail_even_when_match_is_high():
    """Close-up que infla o olho (pagina da banana) nao passa."""
    score = FaceScore(match=0.88, eye_inflate=0.45, geometry=0.9, age=0.9, hair=0.85)
    assert identity_geometry_ok(score, min_match=0.72, max_eye_inflate=0.15) is False
    assert "olhos maiores" in verdict_reason(score, min_match=0.72, max_eye_inflate=0.15)
    assert _ok(score=0.88, eye_inflate=0.45).accepted(0.72) is False


def test_mouth_jaw_age_fail_even_when_still_a_blond_boy():
    """Boca/queixo/idade diferentes: nao basta parecer um menino loiro."""
    score = FaceScore(match=0.80, eye_inflate=0.05, geometry=0.40, age=0.50, hair=0.8)
    assert identity_geometry_ok(score, min_match=0.72, max_eye_inflate=0.15) is False
    assert "boca/queixo" in verdict_reason(score, min_match=0.72, max_eye_inflate=0.15)
    assert _ok(score=0.80, geometry=0.40, age=0.50).accepted(0.72) is False


def test_prefer_verdict_keeps_higher_score():
    low = _ok(score=0.4)
    high = _ok(score=0.9)
    unverified = FaceVerdict("unverified")
    assert prefer_verdict(high, low, 0.72) is True
    assert prefer_verdict(low, high, 0.72) is False
    assert prefer_verdict(high, unverified, 0.72) is True
    assert prefer_verdict(unverified, high, 0.72) is False


def test_prefer_verdict_prefers_smaller_eyes():
    inflated = _ok(score=0.85, eye_inflate=0.5)
    tight = _ok(score=0.84, eye_inflate=0.05)
    assert prefer_verdict(tight, inflated, 0.72) is True
    assert prefer_verdict(inflated, tight, 0.72) is False


@pytest.mark.asyncio
async def test_judge_identity_none_is_unverified_when_configured(monkeypatch):
    from app.ai_clients import identity_lock as mod

    monkeypatch.setattr(mod.settings, "ebook_face_match", True)

    async def none_score(*_a, **_k):
        return None

    lock = build_identity_lock(character_ref=b"AVATAR", face_crop=b"CROP")
    verdict = await judge_identity(lock, b"SCENE", scorer=none_score)
    assert verdict.status == "unverified"
    assert verdict.accepted(0.72) is False


@pytest.mark.asyncio
async def test_judge_identity_none_is_disabled_when_face_match_off(monkeypatch):
    from app.ai_clients import identity_lock as mod

    monkeypatch.setattr(mod.settings, "ebook_face_match", False)

    async def none_score(*_a, **_k):
        return None

    lock = build_identity_lock(character_ref=b"AVATAR", face_crop=b"CROP")
    verdict = await judge_identity(lock, b"SCENE", scorer=none_score)
    assert verdict.status == "disabled"
    assert verdict.accepted(0.72) is True


@pytest.mark.asyncio
async def test_judge_identity_rejects_eye_inflate(monkeypatch):
    from app.ai_clients import identity_lock as mod

    monkeypatch.setattr(mod.settings, "ebook_face_match", True)
    monkeypatch.setattr(mod.settings, "ebook_face_match_min", 0.72)
    monkeypatch.setattr(mod.settings, "ebook_eye_inflate_max", 0.15)

    async def banana(*_a, **_k):
        return FaceScore(match=0.88, eye_inflate=0.42, geometry=0.9, age=0.85, hair=0.8)

    lock = build_identity_lock(character_ref=b"AVATAR", face_crop=b"CROP")
    verdict = await judge_identity(lock, b"SCENE", scorer=banana)
    assert verdict.status == "scored"
    assert verdict.accepted(0.72) is False
    assert verdict.reason == "olhos maiores que a foto/avatar"


@pytest.mark.asyncio
async def test_judge_identity_rejects_geometry_drift(monkeypatch):
    from app.ai_clients import identity_lock as mod

    monkeypatch.setattr(mod.settings, "ebook_face_match", True)
    monkeypatch.setattr(mod.settings, "ebook_face_match_min", 0.72)
    monkeypatch.setattr(mod.settings, "ebook_eye_inflate_max", 0.15)

    async def pineapple(*_a, **_k):
        return FaceScore(match=0.81, eye_inflate=0.08, geometry=0.38, age=0.55, hair=0.8)

    lock = build_identity_lock(character_ref=b"AVATAR", face_crop=b"CROP")
    verdict = await judge_identity(lock, b"SCENE", scorer=pineapple)
    assert verdict.accepted(0.72) is False
    assert "boca/queixo" in verdict.reason


def test_identity_required_error_message():
    assert "character_ref" in IDENTITY_REQUIRED_ERROR
