"""Locked identity reused on every page, extra, and video still.

The approved avatar (`character_ref`) plus the photo face crop are required
for `generate_scene`. Prompt text is not a lock.

A page that fails — low match, inflated eyes, drifted mouth/jaw/age, or
None while the judge is on — is retried, then refused.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.ai_clients.base import ProviderError
from app.ai_clients.face_match import FaceScore, coerce_face_score, score_face_match
from app.config import settings

IDENTITY_REQUIRED_ERROR = "character_ref ausente: a identidade travada e obrigatoria em toda pagina"

IDENTITY_MISMATCH_ERROR = (
    "identidade nao bateu com a crianca da foto/avatar; a pagina nao foi publicada"
)


@dataclass(frozen=True)
class IdentityLock:
    """One locked character, required on every generation that shows the child."""

    character_ref: bytes
    face_crop: bytes | None = None
    photo: bytes | None = None

    def require_character_ref(self) -> bytes:
        return require_character_ref(self.character_ref)

    @property
    def face_truth(self) -> bytes | None:
        """Best likeness reference: detected crop (mouth/chin), else full photo."""
        return self.face_crop or self.photo

    def scene_kwargs(self) -> dict[str, bytes | None]:
        """Keyword args every `generate_scene` call must receive."""
        return {
            "character_ref": self.require_character_ref(),
            "photo": self.face_truth,
        }


def require_character_ref(character_ref: bytes | None) -> bytes:
    if not character_ref:
        raise ProviderError(IDENTITY_REQUIRED_ERROR, transient=False)
    return character_ref


def build_identity_lock(
    *,
    character_ref: bytes | None,
    face_crop: bytes | None = None,
    photo: bytes | None = None,
) -> IdentityLock:
    return IdentityLock(
        character_ref=require_character_ref(character_ref),
        face_crop=face_crop,
        photo=photo,
    )


@dataclass(frozen=True)
class FaceVerdict:
    status: Literal["disabled", "unverified", "scored"]
    score: float | None = None
    eye_inflate: float | None = None
    geometry: float | None = None
    age: float | None = None
    hair: float | None = None
    reason: str = ""

    def accepted(
        self,
        threshold: float,
        *,
        max_eye_inflate: float | None = None,
    ) -> bool:
        if self.status == "disabled":
            return True
        if self.status != "scored" or self.score is None:
            return False
        limit = settings.ebook_eye_inflate_max if max_eye_inflate is None else max_eye_inflate
        return identity_geometry_ok(
            FaceScore(
                match=self.score,
                eye_inflate=self.eye_inflate,
                geometry=self.geometry,
                age=self.age,
                hair=self.hair,
            ),
            min_match=threshold,
            max_eye_inflate=limit,
        )


def identity_geometry_ok(
    score: FaceScore,
    *,
    min_match: float,
    max_eye_inflate: float,
) -> bool:
    """Fail closed: olhos maiores, boca/queixo/idade ou match baixo."""
    if score.match < min_match:
        return False
    if score.eye_inflate is None or score.eye_inflate > max_eye_inflate:
        return False
    if score.geometry is None or score.geometry < min_match:
        return False
    if score.age is None or score.age < min_match:
        return False
    if score.hair is not None and score.hair < min_match:
        return False
    return True


def verdict_reason(score: FaceScore, *, min_match: float, max_eye_inflate: float) -> str:
    if score.eye_inflate is None:
        return "eye_inflate ausente"
    if score.eye_inflate > max_eye_inflate:
        return "olhos maiores que a foto/avatar"
    if score.geometry is None:
        return "geometry ausente"
    if score.geometry < min_match:
        return "boca/queixo/nariz nao batem"
    if score.age is None:
        return "age ausente"
    if score.age < min_match:
        return "idade aparente nao bate"
    if score.hair is not None and score.hair < min_match:
        return "linha do cabelo/risca nao bate"
    if score.match < min_match:
        return "match baixo"
    return ""


def judge_configured() -> bool:
    """Juiz ligado quando ebook_face_match esta on (InsightFace local)."""
    return bool(settings.ebook_face_match)


def prefer_verdict(new: FaceVerdict, old: FaceVerdict, threshold: float) -> bool:
    """Keep the candidate that is closer to a passing likeness."""
    if new.accepted(threshold) and not old.accepted(threshold):
        return True
    if old.accepted(threshold) and not new.accepted(threshold):
        return False
    if new.status == "scored" and old.status == "scored":
        new_eye = new.eye_inflate if new.eye_inflate is not None else 1.0
        old_eye = old.eye_inflate if old.eye_inflate is not None else 1.0
        if new_eye != old_eye:
            return new_eye < old_eye
        return (new.score or 0.0) >= (old.score or 0.0)
    if new.status == "scored" and old.status != "scored":
        return True
    if new.status != "scored" and old.status == "scored":
        return False
    return True


async def _call_scorer(scorer, lock: IdentityLock, truth: bytes, scene: bytes):
    try:
        return await scorer(truth, scene, avatar=lock.character_ref)
    except TypeError:
        try:
            domain = "same" if lock.character_ref else "photo"
            return await scorer(truth, scene, domain=domain)
        except TypeError:
            return await scorer(truth, scene)


async def judge_identity(
    lock: IdentityLock,
    scene: bytes,
    *,
    scorer=score_face_match,
) -> FaceVerdict:
    """Score scene vs photo crop + avatar. None + configured judge = unverified."""
    if not settings.ebook_face_match:
        return FaceVerdict("disabled")
    truth = lock.face_truth or lock.character_ref
    if not truth or not scene:
        return FaceVerdict("unverified", reason="sem recorte/cena")
    try:
        raw = await _call_scorer(scorer, lock, truth, scene)
    except Exception:  # noqa: BLE001 - caller fail-closes on unverified
        return (
            FaceVerdict("unverified", reason="juiz falhou")
            if judge_configured()
            else FaceVerdict("disabled")
        )
    score = coerce_face_score(raw)
    if score is None:
        return (
            FaceVerdict("unverified", reason="sem nota")
            if judge_configured()
            else FaceVerdict("disabled")
        )
    reason = verdict_reason(
        score,
        min_match=settings.ebook_face_match_min,
        max_eye_inflate=settings.ebook_eye_inflate_max,
    )
    return FaceVerdict(
        "scored",
        score=score.match,
        eye_inflate=score.eye_inflate,
        geometry=score.geometry,
        age=score.age,
        hair=score.hair,
        reason=reason,
    )
