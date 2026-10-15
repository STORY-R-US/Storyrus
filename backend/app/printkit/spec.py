"""Especificação de produção. Os números ficam vazios até o template da gráfica."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings


class PrintSpecIncomplete(Exception):
    def __init__(self, gaps: list[str]):
        self.gaps = gaps
        super().__init__(", ".join(gaps))


class PrintPagesMissing(Exception):
    pass


@dataclass(frozen=True)
class PrintSpec:
    bleed_mm: float | None = None
    safety_mm: float | None = None
    spine_mm: float | None = None
    score_mm: float | None = None
    pdf_x: str | None = None
    color_profile: str | None = None
    filename_pattern: str | None = None

    def missing(self, cover_type: str) -> list[str]:
        gaps: list[str] = []
        if self.bleed_mm is None or self.bleed_mm <= 0:
            gaps.append("bleed_mm")
        if self.safety_mm is None or self.safety_mm < 0:
            gaps.append("safety_mm")
        if cover_type == "hard" and (self.spine_mm is None or self.spine_mm <= 0):
            gaps.append("spine_mm")
        if cover_type == "soft" and (self.score_mm is None or self.score_mm <= 0):
            gaps.append("score_mm")
        if not (self.pdf_x or "").strip():
            gaps.append("pdf_x")
        if not (self.color_profile or "").strip():
            gaps.append("color_profile")
        pattern = self.filename_pattern or ""
        if "{code}" not in pattern or "{part}" not in pattern:
            gaps.append("filename_pattern")
        return gaps

    def file_name(self, code: str, part: str) -> str:
        pattern = self.filename_pattern or "{code}-{part}.pdf"
        name = pattern.format(code=code, part=part).replace("\\", "").replace("/", "")
        if not name.lower().endswith(".pdf"):
            name += ".pdf"
        return name


def spec_from_settings() -> PrintSpec:
    return PrintSpec(
        bleed_mm=settings.print_bleed_mm,
        safety_mm=settings.print_safety_mm,
        spine_mm=settings.print_spine_mm,
        score_mm=settings.print_score_mm,
        pdf_x=settings.print_pdf_x,
        color_profile=settings.print_color_profile,
        filename_pattern=settings.print_filename_pattern,
    )


TRIM_MM = {"P": 150.0, "M": 200.0}


def trim_mm(book_size: str) -> float:
    if book_size not in TRIM_MM:
        raise ValueError(book_size)
    return TRIM_MM[book_size]
