"""Dois PDFs de produção: capa (contracapa, lombada ou vinco, capa) e miolo."""

from __future__ import annotations

import io

from PIL import Image as PILImage
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app.printkit.spec import PrintPagesMissing, PrintSpec, PrintSpecIncomplete, trim_mm

PT = 72 / 25.4


def _pt(mm: float) -> float:
    return mm * PT


def _image(raw: bytes) -> ImageReader:
    image = PILImage.open(io.BytesIO(raw)).convert("RGB")
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=92)
    out.seek(0)
    return ImageReader(out)


def _mark(c: canvas.Canvas, code: str, bleed_mm: float) -> None:
    """Código do pedido na sangria, no mesmo canto dos dois arquivos."""
    pad = _pt(bleed_mm) / 5
    font = max(3.0, bleed_mm * 0.35)
    c.setFont("Helvetica", font)
    width = c.stringWidth(code, "Helvetica", font)
    c.setFillColorRGB(1, 1, 1)
    c.rect(pad, pad, width + 2, font + 2, fill=1, stroke=0)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(pad + 1, pad + 1, code)


def _begin(c: canvas.Canvas, code: str, spec: PrintSpec) -> None:
    c.setTitle(code)
    c.setAuthor("StoryUS")
    c.setSubject(
        f"safety_mm={spec.safety_mm}; pdf_x={spec.pdf_x}; color_profile={spec.color_profile}"
    )


def build_print_pdfs(
    *,
    order_code: str,
    book_size: str,
    cover_type: str,
    spec: PrintSpec,
    interior_pages: list[bytes],
) -> tuple[bytes, bytes]:
    gaps = spec.missing(cover_type)
    if gaps:
        raise PrintSpecIncomplete(gaps)
    if not interior_pages:
        raise PrintPagesMissing("O livro ainda não tem páginas ilustradas para o miolo.")
    trim = trim_mm(book_size)
    bleed = float(spec.bleed_mm or 0)
    hinge = float((spec.spine_mm if cover_type == "hard" else spec.score_mm) or 0)
    cover = _cover_pdf(order_code, spec, cover_type, trim, bleed, hinge, interior_pages)
    interior = _interior_pdf(order_code, spec, trim, bleed, interior_pages)
    return cover, interior


def _cover_pdf(
    code: str,
    spec: PrintSpec,
    cover_type: str,
    trim: float,
    bleed: float,
    hinge: float,
    pages: list[bytes],
) -> bytes:
    width = _pt(bleed + trim + hinge + trim + bleed)
    height = _pt(bleed + trim + bleed)
    bleed_pt = _pt(bleed)
    trim_pt = _pt(trim)
    hinge_pt = _pt(hinge)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))
    _begin(c, code, spec)
    back = _image(pages[-1])
    front = _image(pages[0])
    c.drawImage(back, bleed_pt, bleed_pt, trim_pt, trim_pt, preserveAspectRatio=False, anchor="c")
    c.drawImage(
        front,
        bleed_pt + trim_pt + hinge_pt,
        bleed_pt,
        trim_pt,
        trim_pt,
        preserveAspectRatio=False,
        anchor="c",
    )
    c.setFillColorRGB(0.92, 0.92, 0.92)
    c.rect(bleed_pt + trim_pt, bleed_pt, hinge_pt, trim_pt, fill=1, stroke=0)
    if cover_type == "soft":
        c.setStrokeColorRGB(0, 0, 0)
        c.setDash(1, 2)
        c.setLineWidth(0.4)
        for x in (bleed_pt + trim_pt, bleed_pt + trim_pt + hinge_pt):
            c.line(x, 0, x, bleed_pt)
            c.line(x, bleed_pt + trim_pt, x, height)
        c.setDash()
    _mark(c, code, bleed)
    c.showPage()
    c.save()
    return buf.getvalue()


def _interior_pdf(
    code: str,
    spec: PrintSpec,
    trim: float,
    bleed: float,
    pages: list[bytes],
) -> bytes:
    side = _pt(trim + bleed * 2)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(side, side))
    _begin(c, code, spec)
    for raw in pages:
        c.setPageSize((side, side))
        c.drawImage(_image(raw), 0, 0, side, side, preserveAspectRatio=False, anchor="c")
        _mark(c, code, bleed)
        c.showPage()
    c.save()
    return buf.getvalue()
