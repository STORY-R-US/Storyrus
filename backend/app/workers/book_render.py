"""Deterministic Nunito text layer: identical art for the two page deliveries."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

FONT = Path(__file__).resolve().parents[1] / "assets/fonts/Nunito-SemiBold.ttf"
INK = "#172A3A"


def png(data: bytes, *, spread: bool = False) -> bytes:
    with Image.open(io.BytesIO(data)) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        # Crop, never deform square pages. The spread prompt reserves its centre.
        if spread:
            width, height = image.size
            target = (width, width // 2) if width < height * 2 else (height * 2, height)
            image = ImageOps.fit(image, target)
        out = io.BytesIO()
        image.save(out, "PNG")
        return out.getvalue()


def with_text(data: bytes, stanza: str, *, size_cm: int = 20) -> bytes:
    """Only the reserved bottom text band changes; no second image generation."""
    image = Image.open(io.BytesIO(data)).convert("RGB")
    width, height = image.size
    margin = int(width * (10 / (size_cm * 10 + 10)))  # 5mm bleed + 5mm safety
    top = int(height * 0.69)
    draw = ImageDraw.Draw(image)
    words = stanza.splitlines()
    if not words:
        words = [stanza]
    for font_size in range(max(12, width // 30), 9, -1):
        font = ImageFont.truetype(str(FONT), font_size)
        lines = []
        for verse in words:
            line = ""
            for word in verse.split():
                candidate = f"{line} {word}".strip()
                if line and draw.textlength(candidate, font=font) > width - margin * 2 - font_size:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            lines.append(line)
        step = int(font_size * 1.4)
        if len(lines) * step <= height - top - margin:
            break
    else:
        raise ValueError("Estrofe nao cabe na area segura da pagina")
    layer = Image.new("RGBA", image.size)
    ImageDraw.Draw(layer).rectangle(
        (margin, top, width - margin, height - margin), fill=(255, 250, 242, 232)
    )
    image = Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB")
    draw = ImageDraw.Draw(image)
    for index, line in enumerate(lines):
        draw.text(
            (margin + font_size // 2, top + font_size // 3 + index * step),
            line,
            font=font,
            fill=INK,
        )
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def pdf(cover: bytes, pages: list[bytes], *, size_cm: int) -> bytes:
    """Cover + exactly 16 interior pages + back cover, with no extra front matter."""
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen.canvas import Canvas

    if len(pages) != 16:
        raise ValueError("O miolo precisa ter exatamente 16 paginas")
    side = size_cm * 72 / 2.54
    output = io.BytesIO()
    canvas = Canvas(output, pagesize=(side, side))
    for data in [cover, *pages]:
        canvas.drawImage(ImageReader(io.BytesIO(data)), 0, 0, side, side)
        canvas.showPage()
    canvas.setFillColorRGB(1, 0.98, 0.95)
    canvas.rect(0, 0, side, side, stroke=0, fill=1)
    canvas.showPage()
    canvas.save()
    return output.getvalue()
