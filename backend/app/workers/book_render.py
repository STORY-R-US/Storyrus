"""Foto em sangria com o texto desenhado por cima: miolo, capa e contracapa."""

from __future__ import annotations

import io
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

_ASSETS = Path(__file__).resolve().parents[1] / "assets"
FONT = _ASSETS / "fonts/Nunito-SemiBold.ttf"
COVER_FONT = _ASSETS / "fonts/Fredoka-Bold.ttf"
DEDICATION_FONT = _ASSETS / "fonts/PlayfairDisplay-Regular.ttf"
LOGO = _ASSETS / "brand/logo.png"
QR = _ASSETS / "brand/qr-storyrus.png"
INK = "#172A3A"
NAVY = (23, 42, 58)
GOLD = (244, 196, 48)
BLEED_MM = 5
# Mesma definição do PDF de referência: 210 mm com a foto em cerca de 159 dpi.
TARGET_PX = 1316


def preview_watermark(data: bytes) -> bytes:
    """Repete a marca na imagem da prévia. O original do livro não passa por aqui."""
    base = Image.open(io.BytesIO(data)).convert("RGBA")
    width, height = base.size
    stamp = Image.new("RGBA", (width * 3, height * 3), (0, 0, 0, 0))
    draw = ImageDraw.Draw(stamp)
    font = ImageFont.truetype(str(FONT), max(28, min(width, height) // 12))
    label = "PRÉVIA  ·  storyrus.ai"
    span = int(draw.textlength(label, font=font)) + font.size // 2
    step_y = int(font.size * 1.7)
    y = 0
    row = 0
    while y < stamp.height:
        x = -(span // 2) if row % 2 else 0
        while x < stamp.width:
            draw.text((x + 1, y + 1), label, font=font, fill=(23, 42, 58, 150))
            draw.text((x, y), label, font=font, fill=(255, 255, 255, 180))
            x += span
        y += step_y
        row += 1
    stamp = stamp.rotate(-24, resample=Image.Resampling.BICUBIC, expand=True)
    left = max(0, (stamp.width - width) // 2)
    top = max(0, (stamp.height - height) // 2)
    stamp = stamp.crop((left, top, left + width, top + height))
    marked = Image.alpha_composite(base, stamp).convert("RGB")
    out = io.BytesIO()
    marked.save(out, "PNG")
    return out.getvalue()


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


def covers_pdf(back: bytes, front: bytes, *, size_cm: int, title: str = "") -> bytes:
    """Contracapa e capa em páginas separadas, na ordem do PDF de referência."""
    return _pages_pdf([back, front], size_cm=size_cm, title=title)


def shop_pdfs(
    front: bytes,
    back: bytes,
    pages: list[bytes],
    *,
    dedication: str | None,
    size_cm: int,
    title: str = "",
) -> tuple[bytes, bytes]:
    """Capa/contracapa separadas e miolo com ímpares espelhadas, dedicatória e sangria."""
    covers = covers_pdf(back, front, size_cm=size_cm, title=title)
    interior = interior_pdf(pages, dedication=dedication, size_cm=size_cm, title=title)
    return covers, interior


def interior_pdf(
    pages: list[bytes], *, dedication: str | None, size_cm: int, title: str = ""
) -> bytes:
    """Miolo em 210 mm. Página ímpar é espelhada. A dedicatória fecha o arquivo."""
    frames = [
        _print_page(raw, number, mirror=number % 2 == 1) for number, raw in enumerate(pages, start=1)
    ]
    frames.append(dedication_page(dedication or ""))
    return _pages_pdf(frames, size_cm=size_cm, title=title)


def _print_page(raw: bytes, number: int, *, mirror: bool) -> bytes:
    image = Image.open(io.BytesIO(raw)).convert("RGB")
    image = image.resize((TARGET_PX, TARGET_PX), Image.Resampling.LANCZOS)
    _page_badge(image, number)
    if mirror:
        image = ImageOps.mirror(image)
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def _page_badge(image: Image.Image, number: int) -> None:
    """Número no canto inferior esquerdo. O espelho da página ímpar leva o número à direita."""
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(FONT), max(22, TARGET_PX // 46))
    label = str(number)
    text_w = draw.textlength(label, font=font)
    pad_x = int(font.size * 0.72)
    pad_y = int(font.size * 0.38)
    width = int(text_w + pad_x * 2)
    height = font.size + pad_y * 2
    margin = int(TARGET_PX * (14 / 210))
    x0 = margin
    y0 = image.height - margin - height
    draw.rounded_rectangle((x0, y0, x0 + width, y0 + height), radius=height / 2, fill=(255, 255, 255))
    draw.text((x0 + pad_x, y0 + pad_y * 0.45), label, font=font, fill=NAVY)


def dedication_page(text: str) -> bytes:
    """Página branca de dedicatória, no fechamento do miolo."""
    image = Image.new("RGB", (TARGET_PX, TARGET_PX), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    _dedication_corners(draw, TARGET_PX)
    title_font = ImageFont.truetype(str(DEDICATION_FONT), int(TARGET_PX * 0.055))
    title = "Dedicatória"
    title_w = draw.textlength(title, font=title_font)
    title_y = int(TARGET_PX * 0.16)
    draw.text(((TARGET_PX - title_w) / 2, title_y), title, font=title_font, fill=NAVY)
    heart_y = title_y + title_font.size + int(TARGET_PX * 0.02)
    _star(draw, TARGET_PX // 2, heart_y, max(8, TARGET_PX // 90))
    body = (text or "").strip()
    if body:
        column = int(TARGET_PX * 0.62)
        font = ImageFont.truetype(str(FONT), int(TARGET_PX * 0.028))
        lines = _wrap(draw, body, font, column)
        step = int(font.size * 1.45)
        y = int(TARGET_PX * 0.42)
        for line in lines:
            drawn = draw.textlength(line, font=font)
            draw.text(((TARGET_PX - drawn) / 2, y), line, font=font, fill=NAVY)
            y += step
    if LOGO.exists():
        logo = _logo()
        logo_h = int(TARGET_PX * 0.07)
        logo_w = max(1, int(logo.width * logo_h / logo.height))
        logo = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
        faded = Image.new("RGBA", logo.size, (255, 255, 255, 0))
        faded.paste(logo, (0, 0))
        pixels = [(r, g, b, min(a, 48)) for r, g, b, a in faded.getdata()]
        faded.putdata(pixels)
        image.paste(faded, ((TARGET_PX - logo_w) // 2, int(TARGET_PX * 0.72)), faded)
    else:
        mark = ImageFont.truetype(str(FONT), int(TARGET_PX * 0.035))
        label = "STORY R US"
        drawn = draw.textlength(label, font=mark)
        draw.text(((TARGET_PX - drawn) / 2, int(TARGET_PX * 0.74)), label, font=mark, fill=(210, 214, 220))
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def _dedication_corners(draw: ImageDraw.ImageDraw, side: int) -> None:
    blue = (126, 176, 214)
    clusters = (
        (int(side * 0.08), int(side * 0.08), 1, 1),
        (int(side * 0.92), int(side * 0.08), -1, 1),
        (int(side * 0.08), int(side * 0.92), 1, -1),
        (int(side * 0.92), int(side * 0.92), -1, -1),
    )
    for cx, cy, flip_x, flip_y in clusters:
        _star(draw, cx, cy, side // 48)
        _star(draw, cx + flip_x * side // 28, cy + flip_y * side // 40, side // 70)
        draw.ellipse(
            (
                cx + flip_x * side // 18 - side // 90,
                cy + flip_y * side // 22 - side // 90,
                cx + flip_x * side // 18 + side // 90,
                cy + flip_y * side // 22 + side // 90,
            ),
            fill=blue,
        )


def _pages_pdf(frames: list[bytes], *, size_cm: int, title: str = "") -> bytes:
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen.canvas import Canvas

    # 20 cm de corte + 5 mm de sangria de cada lado = 210 mm.
    side = (size_cm * 10 + BLEED_MM * 2) * 72 / 25.4
    output = io.BytesIO()
    canvas = Canvas(output, pagesize=(side, side))
    if title:
        canvas.setTitle(f"STORY R US - {title}")
    canvas.setAuthor("STORY R US")
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
