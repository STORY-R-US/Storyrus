"""Foto em sangria com o texto desenhado por cima: miolo, capa e contracapa."""

from __future__ import annotations

import io
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

_ASSETS = Path(__file__).resolve().parents[1] / "assets"
FONT = _ASSETS / "fonts/Nunito-SemiBold.ttf"
COVER_FONT = _ASSETS / "fonts/Fredoka-Bold.ttf"
LOGO = _ASSETS / "brand/logo.png"
QR = _ASSETS / "brand/qr-storyrus.png"
INK = "#172A3A"
NAVY = (23, 42, 58)
GOLD = (244, 196, 48)
BLEED_MM = 5
# Mesma definição do PDF de referência: 210 mm com a foto em cerca de 159 dpi.
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


def front_cover(data: bytes, title: str) -> bytes:
    """Título no céu da capa, em Fredoka azul-marinho, sem faixa sobre a foto."""
    image = Image.open(io.BytesIO(data)).convert("RGB")
    width, height = image.size
    draw = ImageDraw.Draw(image)
    max_width = int(width * 0.78)
    top = int(height * 0.07)
    ceiling = int(height * 0.38)
    font, lines, gap = _fit_title(draw, title, max_width, ceiling - top)
    block = len(lines) * (font.size + gap)
    y = top
    center = width // 2
    _star(draw, center - max_width // 2, y + font.size // 2, width // 28)
    _star(draw, center + max_width // 2, y + block // 2, width // 34)
    _star(draw, center, y + block + width // 40, width // 42)
    for line in lines:
        drawn = draw.textlength(line, font=font)
        draw.text(((width - drawn) / 2, y), line, font=font, fill=NAVY)
        y += font.size + gap
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def back_cover(data: bytes) -> bytes:
    """Marca, QR e storyrus.ai no céu da contracapa. A foto de baixo permanece."""
    image = Image.open(io.BytesIO(data)).convert("RGB")
    width, height = image.size
    logo = _logo()
    logo_h = int(height * 0.18)
    logo_w = max(1, int(logo.width * logo_h / logo.height))
    if logo_w > int(width * 0.62):
        logo_w = int(width * 0.62)
        logo_h = max(1, int(logo.height * logo_w / logo.width))
    logo = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
    y = int(height * 0.045)
    image.paste(logo, ((width - logo_w) // 2, y), logo)
    y += logo_h + int(height * 0.012)
    draw = ImageDraw.Draw(image)
    tag = ImageFont.truetype(str(FONT), max(14, width // 30))
    _centered(draw, "LIVROS PERSONALIZADOS", tag, y, width)
    y += tag.size + int(height * 0.016)
    qr = Image.open(QR).convert("RGBA")
    qr_side = int(width * 0.16)
    qr = qr.resize((qr_side, qr_side), Image.Resampling.NEAREST)
    image.paste(qr, ((width - qr_side) // 2, y), qr)
    y += qr_side + int(height * 0.012)
    small = ImageFont.truetype(str(FONT), max(13, width // 34))
    site = ImageFont.truetype(str(FONT), max(16, width // 24))
    _centered(draw, "VISITE NOSSO SITE", small, y, width)
    _centered(draw, "storyrus.ai", site, y + small.size + 2, width)
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def pdf(cover: bytes, pages: list[bytes], back: bytes, *, size_cm: int) -> bytes:
    """Capa, 16 páginas de miolo e contracapa, cada uma em sangria de 5 mm."""
    if len(pages) != 16:
        raise ValueError("O miolo precisa ter exatamente 16 paginas")
    return _pages_pdf([cover, *pages, back], size_cm=size_cm)


def covers_pdf(back: bytes, front: bytes, *, size_cm: int) -> bytes:
    """Contracapa e capa em páginas separadas, na ordem do PDF de referência."""
    return _pages_pdf([back, front], size_cm=size_cm)


def _pages_pdf(frames: list[bytes], *, size_cm: int) -> bytes:
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen.canvas import Canvas

    # 20 cm de corte + 5 mm de sangria de cada lado = 210 mm.
    side = (size_cm * 10 + BLEED_MM * 2) * 72 / 25.4
    output = io.BytesIO()
    canvas = Canvas(output, pagesize=(side, side))
    for data in frames:
        frame = Image.open(io.BytesIO(data)).convert("RGB")
        if frame.size != (TARGET_PX, TARGET_PX):
            frame = frame.resize((TARGET_PX, TARGET_PX), Image.Resampling.LANCZOS)
        encoded = io.BytesIO()
        frame.save(encoded, "JPEG", quality=92)
        encoded.seek(0)
        canvas.drawImage(ImageReader(encoded), 0, 0, side, side)
        canvas.showPage()
    canvas.save()
    return output.getvalue()


def _fit_title(draw: ImageDraw.ImageDraw, title: str, max_width: int, max_height: int):
    for font_size in range(max(28, max_width // 6), 15, -2):
        font = ImageFont.truetype(str(COVER_FONT), font_size)
        lines = _wrap(draw, title, font, max_width)
        gap = max(2, int(font_size * 0.12))
        if len(lines) * (font_size + gap) <= max_height:
            return font, lines, gap
    font = ImageFont.truetype(str(COVER_FONT), 16)
    return font, _wrap(draw, title, font, max_width), 2


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int):
    lines: list[str] = []
    for verse in [part.strip() for part in text.splitlines() if part.strip()] or [text]:
        line = ""
        for word in verse.split():
            candidate = f"{line} {word}".strip()
            if draw.textlength(candidate, font=font) <= max_width:
                line = candidate
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)
    return lines or [text]


def _centered(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, y: int, width: int
):
    drawn = draw.textlength(text, font=font)
    draw.text(((width - drawn) / 2, y), text, font=font, fill=NAVY)


def _star(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int) -> None:
    points = []
    for step in range(10):
        angle = -math.pi / 2 + step * math.pi / 5
        arm = radius if step % 2 == 0 else radius * 0.42
        points.append((cx + arm * math.cos(angle), cy + arm * math.sin(angle)))
    draw.polygon(points, fill=GOLD)


def _logo() -> Image.Image:
    image = Image.open(LOGO).convert("RGBA")
    pixels = []
    for red, green, blue, alpha in image.getdata():
        if red < 22 and green < 22 and blue < 22:
            pixels.append((red, green, blue, 0))
        else:
            pixels.append((red, green, blue, alpha))
    image.putdata(pixels)
    return image
