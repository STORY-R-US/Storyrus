"""Deterministic Nunito text layer: identical art for the two page deliveries."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

FONT = Path(__file__).resolve().parents[1] / "assets/fonts/Nunito-SemiBold.ttf"
INK = "#172A3A"
BLEED_MM = 5
# Mesma definição do miolo de referência: 210 mm com a foto em cerca de 159 dpi.
TARGET_PX = 1316


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


def with_text(data: bytes, stanza: str, *, size_cm: int = 20, page: int = 1) -> bytes:
    """Verso no céu, como o miolo: bloco azul, sem faixa e sem número de página.

    Página ímpar fica à direita; par, à esquerda. A foto embaixo do bloco não muda.
    """
    image = Image.open(io.BytesIO(data)).convert("RGB")
    width, height = image.size
    margin = int(width * ((BLEED_MM + 5) / (size_cm * 10 + BLEED_MM * 2)))
    column = int(width * 0.42)
    on_right = page % 2 == 1
    x0 = width - margin - column if on_right else margin
    words = [line for line in stanza.splitlines() if line.strip()] or [stanza]
    draw = ImageDraw.Draw(image)
    ceiling = int(height * 0.46)
    for font_size in range(max(18, width // 22), 11, -1):
        font = ImageFont.truetype(str(FONT), font_size)
        lines: list[str] = []
        for verse in words:
            line = ""
            for word in verse.split():
                candidate = f"{line} {word}".strip()
                if line and draw.textlength(candidate, font=font) > column:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            if line:
                lines.append(line)
        step = int(font_size * 1.28)
        if margin + len(lines) * step <= ceiling:
            break
    else:
        raise ValueError("Estrofe nao cabe na area segura da pagina")
    for index, line in enumerate(lines):
        draw.text((x0, margin + index * step), line, font=font, fill=INK)
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def pdf(cover: bytes, pages: list[bytes], *, size_cm: int) -> bytes:
    """Cover + exactly 16 interior pages + back cover, with no extra front matter."""
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen.canvas import Canvas

    if len(pages) != 16:
        raise ValueError("O miolo precisa ter exatamente 16 paginas")
    # 20 cm de corte + 5 mm de sangria de cada lado = 210 mm, como o miolo de referência.
    side = (size_cm * 10 + BLEED_MM * 2) * 72 / 25.4
    output = io.BytesIO()
    canvas = Canvas(output, pagesize=(side, side))
    for data in [cover, *pages]:
        frame = Image.open(io.BytesIO(data)).convert("RGB")
        if frame.size != (TARGET_PX, TARGET_PX):
            frame = frame.resize((TARGET_PX, TARGET_PX), Image.Resampling.LANCZOS)
        encoded = io.BytesIO()
        frame.save(encoded, "JPEG", quality=92)
        encoded.seek(0)
        canvas.drawImage(ImageReader(encoded), 0, 0, side, side)
        canvas.showPage()
    canvas.setFillColorRGB(1, 0.98, 0.95)
    canvas.rect(0, 0, side, side, stroke=0, fill=1)
    canvas.showPage()
    canvas.save()
    return output.getvalue()
