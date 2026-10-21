"""Testes do lote de avatares das criancas aprovadas (sem Gemini)."""

from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path

from PIL import Image

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "scripts"))

import gen_avatars_aprovados as av  # noqa: E402


def _png(path: Path, color: str = "white") -> None:
    buf = BytesIO()
    Image.new("RGB", (80, 80), color).save(buf, format="PNG")
    path.write_bytes(buf.getvalue())


def test_slugify_strips_accents():
    assert av.slugify("Emília") == "emilia"
    assert av.slugify("Facundo") == "facundo"
    assert av.slugify("Martin 2") == "martin-2"


def test_discover_flat_photos_skips_avatars(tmp_path):
    _png(tmp_path / "Emilia.jpg")
    _png(tmp_path / "Martin.png")
    _png(tmp_path / "Facundo.jpeg")
    _png(tmp_path / "avatar-emilia.png")
    rows = av.discover(tmp_path)
    assert [c.slug for c in rows] == ["emilia", "facundo", "martin"]
    assert rows[0].published.name == "avatar-emilia.png"


def test_discover_one_folder_per_child(tmp_path):
    (tmp_path / "Emilia").mkdir()
    (tmp_path / "Martin").mkdir()
    _png(tmp_path / "Emilia" / "foto.jpg")
    _png(tmp_path / "Martin" / "a.png")
    rows = av.discover(tmp_path)
    assert [c.slug for c in rows] == ["emilia", "martin"]
    assert rows[0].photo.name == "foto.jpg"


def test_children_filters_and_rejects_unknown(tmp_path):
    _png(tmp_path / "Emilia.jpg")
    _png(tmp_path / "Facundo.jpg")
    got = av.children(["FACUNDO"], photos_dir=tmp_path)
    assert [c.slug for c in got] == ["facundo"]
    try:
        av.children(["pai"], photos_dir=tmp_path)
    except ValueError as exc:
        assert "pai" in str(exc)
    else:
        raise AssertionError("esperava ValueError")


def test_out_dir_does_not_touch_book_character(tmp_path, monkeypatch):
    monkeypatch.setattr(av, "BASE_OUT", tmp_path / "aprovados")
    monkeypatch.setattr(av, "BOOK_CHAR", tmp_path / "amazonia-matteo" / "character.png")
    child = av.Child("emilia", tmp_path / "Emilia.jpg")
    assert child.out_dir != av.BOOK_CHAR.parent
    assert child.out_dir.name == "emilia"
    assert "amazonia-matteo" not in child.out_dir.parts


def test_contact_sheet_writes_four_cells(tmp_path, monkeypatch):
    monkeypatch.setattr(av, "BASE_OUT", tmp_path / "aprovados")
    monkeypatch.setattr(av, "BOOK_CHAR", tmp_path / "amazonia-matteo" / "character.png")
    photo = tmp_path / "Emilia.jpg"
    _png(photo, "red")
    child = av.Child("emilia", photo)
    child.out_dir.mkdir(parents=True)
    _png(child.out_dir / "face-crop.jpg", "blue")
    _png(child.out_dir / "character-raw.png", "green")
    _png(child.out_dir / "character.png", "yellow")
    sheet = av.contact_sheet(child)
    im = Image.open(sheet)
    assert im.size == (av.CELL * 4, av.CELL + 22)
