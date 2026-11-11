import io

import pytest
from fastapi import HTTPException
from PIL import Image

from app.routers.projects import photos


def encoded(image, kind="PNG", **options):
    buffer = io.BytesIO()
    image.save(buffer, kind, **options)
    return buffer.getvalue()


def test_normalization_flattens_transparency_resizes_and_removes_metadata():
    raw = encoded(Image.new("RGBA", (4096, 2048), (0, 0, 0, 0)))
    with Image.open(io.BytesIO(photos._normalize_photo(raw))) as image:
        assert image.format == "JPEG"
        assert image.size == (2048, 1024)
        assert image.getpixel((0, 0)) == (255, 255, 255)
        assert not image.getexif()


def test_normalization_applies_exif_orientation_before_removing_it():
    exif = Image.Exif()
    exif[274] = 6
    raw = encoded(Image.new("RGB", (20, 10), "blue"), "JPEG", exif=exif)
    with Image.open(io.BytesIO(photos._normalize_photo(raw))) as image:
        assert image.size == (10, 20)
        assert not image.getexif()


@pytest.mark.parametrize("data", [b"", b"not a photo", encoded(Image.new("RGB", (4, 4)), "GIF")])
def test_normalization_rejects_unreadable_or_unsupported_files(data):
    with pytest.raises(HTTPException) as caught:
        photos._normalize_photo(data)
    assert caught.value.status_code == 400


def test_normalization_checks_pixels_before_decoding(monkeypatch):
    monkeypatch.setattr(photos, "_MAX_PIXELS", 10)
    with pytest.raises(HTTPException):
        photos._normalize_photo(encoded(Image.new("RGB", (4, 4))))
