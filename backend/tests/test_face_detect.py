"""Testes da deteccao de rosto InsightFace (sem rede / sem buffalo_l).

O que importa: nenhuma falha de deteccao pode impedir o avatar, e caixas
implausiveis sao rejeitadas a favor do recorte geometrico.
"""

from io import BytesIO

import pytest
from PIL import Image

from app.ai_clients import face_detect as fd


def _png(w: int = 400, h: int = 600) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (w, h), (30, 90, 40)).save(buf, format="PNG")
    return buf.getvalue()


def test_pick_child_box_prefers_smaller_face():
    size = (400, 600)
    adult = (20, 20, 200, 220)
    child = (250, 80, 330, 180)
    assert fd.pick_child_box([adult, child], size) == child


def test_pick_child_box_rejects_near_full_frame():
    size = (400, 600)
    huge = (0, 0, 400, 600)
    assert fd.pick_child_box([huge], size) is None


def test_pick_child_box_rejects_tiny():
    size = (400, 600)
    assert fd.pick_child_box([(10, 10, 20, 20)], size) is None


def test_detect_face_box_uses_insightface(monkeypatch):
    monkeypatch.setattr(fd, "face_boxes", lambda _p: [(100, 60, 300, 300)])
    assert fd.detect_face_box(_png(400, 600)) == (100, 60, 300, 300)


def test_detect_face_box_survives_empty(monkeypatch):
    monkeypatch.setattr(fd, "face_boxes", lambda _p: [])
    assert fd.detect_face_box(_png()) is None


def test_detect_face_box_survives_exception(monkeypatch):
    def boom(_p):
        raise RuntimeError("buffalo down")

    monkeypatch.setattr(fd, "face_boxes", boom)
    assert fd.detect_face_box(_png()) is None


@pytest.mark.asyncio
async def test_face_reference_falls_back_to_geometric_crop(monkeypatch):
    monkeypatch.setattr(fd, "face_boxes", lambda _p: [])
    photo = _png(400, 600)
    crop = await fd.face_reference(photo)
    assert crop != photo
    assert Image.open(BytesIO(crop)).size[0] < 400


@pytest.mark.asyncio
async def test_identity_images_uses_the_detected_crop(monkeypatch):
    monkeypatch.setattr(fd, "face_boxes", lambda _p: [(100, 60, 300, 300)])
    photo = _png(400, 600)
    refs = await fd.identity_images(photo)
    assert len(refs) == 2
    assert refs[1] == photo
    # Caixa de 200x240 px + folga de 12% (24 em x, 28 em y) em cada lado.
    assert Image.open(BytesIO(refs[0])).size == (248, 296)
