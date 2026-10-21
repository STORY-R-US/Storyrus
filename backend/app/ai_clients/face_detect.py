"""Localiza o rosto da crianca na foto, para o recorte de identidade.

InsightFace lista os rostos; em fotos com adulto + crianca no colo escolhemos
o menor bbox (crianca tipicamente menor). Sem detector local, cai no recorte
geometrico de `face_ref` (offline). Nenhum avatar deixa de sair por causa disto.
"""

from __future__ import annotations

import asyncio
import logging
from io import BytesIO

from PIL import Image

from app.ai_clients.face_match import face_boxes
from app.ai_clients.face_ref import isolate_on_cream, try_face_crop

logger = logging.getLogger(__name__)

_MIN_FACE_SIDE = 16
# Caixa que cobre quase a foto inteira nao e um recorte util.
_MAX_FACE_AREA_FRAC = 0.92


def _box_area(box: tuple[int, int, int, int]) -> float:
    left, top, right, bottom = box
    return float(max(0, right - left) * max(0, bottom - top))


def _plausible(box: tuple[int, int, int, int], size: tuple[int, int]) -> bool:
    left, top, right, bottom = box
    if right - left < _MIN_FACE_SIDE or bottom - top < _MIN_FACE_SIDE:
        return False
    w, h = size
    if w <= 0 or h <= 0:
        return False
    if _box_area(box) > _MAX_FACE_AREA_FRAC * w * h:
        return False
    if left < 0 or top < 0 or right > w or bottom > h:
        # Clip leve ainda e util.
        if right <= left or bottom <= top:
            return False
    return True


def pick_child_box(
    boxes: list[tuple[int, int, int, int]], size: tuple[int, int]
) -> tuple[int, int, int, int] | None:
    """Menor rosto plausivel (crianca no colo); senao o unico/maior restante."""
    plausible = [b for b in boxes if _plausible(b, size)]
    if not plausible:
        return None
    if len(plausible) == 1:
        return plausible[0]
    return min(plausible, key=_box_area)


def detect_face_box(photo: bytes) -> tuple[int, int, int, int] | None:
    """Caixa do rosto em pixels via InsightFace, ou None."""
    try:
        size = Image.open(BytesIO(photo)).size
    except Exception:  # noqa: BLE001 - nao e imagem valida
        return None
    try:
        boxes = face_boxes(photo)
    except Exception as exc:  # noqa: BLE001 - pre-processamento nunca derruba
        logger.warning("InsightFace face detect falhou: %s", exc)
        return None
    return pick_child_box(boxes, size)


async def face_reference(photo: bytes) -> bytes:
    """Recorte do rosto para lock de identidade: detectado, ou heuristico.

    InsightFace carrega o modelo na primeira foto. Fora da thread isso
    trava o event loop da API (health check e o pump da prévia).
    """
    box = await asyncio.to_thread(detect_face_box, photo)
    if box is None:
        logger.info("Sem caixa de rosto; usando o recorte geometrico de fallback")
        return try_face_crop(photo)
    try:
        return isolate_on_cream(photo, box)
    except Exception as exc:  # noqa: BLE001 - recorte nunca deve derrubar o avatar
        logger.warning("Recorte pela caixa falhou (%s); caindo no heuristico", exc)
        return try_face_crop(photo)


async def identity_images(photo: bytes) -> list[bytes]:
    """[recorte do rosto, foto inteira] para `generate_character`."""
    crop = await face_reference(photo)
    if crop == photo:
        return [photo]
    return [crop, photo]
