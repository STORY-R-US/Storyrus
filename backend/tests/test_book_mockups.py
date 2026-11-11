"""Deterministic book presentations preserve the project's exact artwork."""

import hashlib
import io

from PIL import Image

from app.workers import book_mockups


def _square_png(color):
    output = io.BytesIO()
    Image.new("RGB", (128, 128), color).save(output, "PNG")
    return output.getvalue()


def test_open_book_spread_projects_both_exact_page_sources():
    left = _square_png((220, 35, 45))
    right = _square_png((30, 65, 220))

    data, provenance = book_mockups.open_book_spread(left, right)

    image = Image.open(io.BytesIO(data))
    assert image.format == "PNG"
    assert image.size == (2048, 1024)
    assert provenance["sources"] == [
        hashlib.sha256(left).hexdigest(),
        hashlib.sha256(right).hexdigest(),
    ]
    assert image.getpixel((512, 512))[0] > image.getpixel((512, 512))[2]
    assert image.getpixel((1536, 512))[2] > image.getpixel((1536, 512))[0]


def test_book_only_fallback_uses_the_exact_cover_and_declares_its_presentation():
    cover = _square_png((180, 80, 40))

    data, provenance = book_mockups.book_only(cover)

    image = Image.open(io.BytesIO(data))
    assert image.format == "PNG"
    assert image.size == (1024, 1024)
    assert provenance["source"] == hashlib.sha256(cover).hexdigest()
    assert provenance["presentation"] == "book_only_fallback"
    assert image.getpixel((520, 420))[0] > image.getpixel((520, 420))[2]
