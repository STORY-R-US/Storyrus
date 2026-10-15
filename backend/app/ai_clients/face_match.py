"""Compara o rosto da foto com o protagonista de uma cena do livro.

Backend unico: cosine InsightFace (local). Sem Gemini.
Na cena, o juiz pega o rosto mais proximo do recorte — nao o maior bbox
(adulto, animal ou objeto grande nao podem sequestrar a nota).
Qualquer falha devolve None. `identity_accepted(None)` ainda e True (legado);
o portao fail-closed mora em `identity_lock.judge_identity`.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from io import BytesIO

from app.config import settings

logger = logging.getLogger(__name__)

# ArcFace foto x ilustracao: mesmo rosto costuma cair ~0.25–0.55, nao 0.85.
_ARC_COSINE_LO = 0.18
_ARC_COSINE_HI = 0.52
# Avatar x cena (os dois ilustrados): o mesmo rosto sobe; o mapa da foto infla.
_ARC_SAME_LO = 0.32
_ARC_SAME_HI = 0.62

_insightface_app = None


@dataclass(frozen=True)
class FaceScore:
    """Notas 0–1. InsightFace preenche geometry/age/hair com o match."""

    match: float
    eye_inflate: float | None = None
    geometry: float | None = None
    age: float | None = None
    hair: float | None = None


def coerce_face_score(raw) -> FaceScore | None:
    """Aceita FaceScore, float (mocks) ou None."""
    if raw is None:
        return None
    if isinstance(raw, FaceScore):
        return FaceScore(
            match=raw.match,
            eye_inflate=0.0 if raw.eye_inflate is None else raw.eye_inflate,
            geometry=raw.match if raw.geometry is None else raw.geometry,
            age=raw.match if raw.age is None else raw.age,
            hair=raw.match if raw.hair is None else raw.hair,
        )
    if isinstance(raw, (int, float)) and raw == raw:
        value = max(0.0, min(1.0, float(raw)))
        return FaceScore(match=value, eye_inflate=0.0, geometry=1.0, age=1.0, hair=1.0)
    return None


def identity_accepted(score: float | None, *, min_score: float | None = None) -> bool:
    """None = sem rosto/nota: nao bloqueia. Abaixo do limiar = recusa."""
    if score is None:
        return True
    threshold = settings.ebook_face_match_min if min_score is None else min_score
    return score >= threshold


def cosine_bounds(domain: str = "photo") -> tuple[float, float]:
    """Limites ArcFace: foto x ilustracao, ou avatar x cena (mesmo estilo)."""
    if (domain or "photo").strip().lower() == "same":
        return _ARC_SAME_LO, _ARC_SAME_HI
    return _ARC_COSINE_LO, _ARC_COSINE_HI


def match_from_cosine(
    sim: float, *, lo: float | None = None, hi: float | None = None, domain: str = "photo"
) -> float:
    """Mapeia cosine ArcFace para nota 0–1 do juiz."""
    if lo is None or hi is None:
        lo, hi = cosine_bounds(domain)
    if hi <= lo:
        return 0.0
    return max(0.0, min(1.0, (float(sim) - lo) / (hi - lo)))


def _cosine(a, b) -> float:
    import numpy as np

    va = np.asarray(a, dtype=np.float64).ravel()
    vb = np.asarray(b, dtype=np.float64).ravel()
    na = float(np.linalg.norm(va))
    nb = float(np.linalg.norm(vb))
    if na < 1e-8 or nb < 1e-8:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


def _insightface_analyzer():
    global _insightface_app
    if _insightface_app is None:
        from insightface.app import FaceAnalysis

        app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        app.prepare(ctx_id=-1, det_size=(640, 640))
        _insightface_app = app
    return _insightface_app


def insightface_available() -> bool:
    """True se o analyzer local puder ser carregado."""
    try:
        _insightface_analyzer()
        return True
    except Exception:  # noqa: BLE001
        return False


def _face_area(face) -> float:
    box = getattr(face, "bbox", None)
    if box is None or len(box) < 4:
        return 0.0
    return float((box[2] - box[0]) * (box[3] - box[1]))


def _face_embedding(face):
    emb = getattr(face, "normed_embedding", None)
    if emb is None:
        emb = getattr(face, "embedding", None)
    return emb


def _pick_embedding(faces, *, probe=None):
    """Um embedding: maior bbox no recorte, ou o mais proximo do `probe` na cena.

    Sem probe o recorte da crianca e um close — o maior rosto e o certo.
    Com probe (embedding da foto) a cena pode ter adulto, bicho ou close de
    objeto: pega o rosto mais parecido com a crianca, nao o maior do quadro.
    """
    scored: list[tuple[object, object]] = []
    for face in faces or []:
        emb = _face_embedding(face)
        if emb is None:
            continue
        scored.append((face, emb))
    if not scored:
        return None
    if probe is None:
        return max(scored, key=lambda pair: _face_area(pair[0]))[1]
    return max(scored, key=lambda pair: _cosine(probe, pair[1]))[1]


def _faces_in(image_bytes: bytes) -> list:
    import numpy as np
    from PIL import Image

    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    bgr = np.asarray(img)[:, :, ::-1].copy()
    return list(_insightface_analyzer().get(bgr) or [])


def face_boxes(image_bytes: bytes) -> list[tuple[int, int, int, int]]:
    """Caixas InsightFace (left, top, right, bottom). Vazio se falhar."""
    try:
        faces = _faces_in(image_bytes)
    except Exception:  # noqa: BLE001 - detect e best-effort
        return []
    out: list[tuple[int, int, int, int]] = []
    for face in faces:
        box = getattr(face, "bbox", None)
        if box is None or len(box) < 4:
            continue
        left, top, right, bottom = (int(box[0]), int(box[1]), int(box[2]), int(box[3]))
        if right - left < 8 or bottom - top < 8:
            continue
        out.append((left, top, right, bottom))
    return out


def _embedding_of(image_bytes: bytes, *, probe=None):
    return _pick_embedding(_faces_in(image_bytes), probe=probe)


def _score_insightface(photo: bytes, scene: bytes, *, domain: str = "photo") -> FaceScore | None:
    try:
        a = _embedding_of(photo)
        b = _embedding_of(scene, probe=a) if a is not None else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("InsightFace falhou: %s", exc)
        return None
    if a is None or b is None:
        logger.warning("InsightFace nao detectou rosto na foto ou na cena")
        return None
    match = match_from_cosine(_cosine(a, b), domain=domain)
    return FaceScore(
        match=match,
        eye_inflate=0.0,
        geometry=match,
        age=match,
        hair=match,
    )


async def score_face_match_detail(
    photo: bytes,
    scene: bytes,
    *,
    domain: str = "photo",
    avatar: bytes | None = None,
) -> FaceScore | None:
    """FaceScore de identidade probe x cena, ou None se nao der para confiar."""
    _ = avatar
    if not photo or not scene:
        return None
    return await asyncio.to_thread(_score_insightface, photo, scene, domain=domain)


async def score_face_match(
    photo: bytes,
    scene: bytes,
    *,
    domain: str = "photo",
    avatar: bytes | None = None,
) -> float | None:
    """Nota 0–1 de identidade probe x cena, ou None se nao der para confiar.

    `domain=photo`: recorte real x ilustracao. `domain=same`: avatar x cena.
    """
    scored = await score_face_match_detail(photo, scene, domain=domain, avatar=avatar)
    return None if scored is None else scored.match
