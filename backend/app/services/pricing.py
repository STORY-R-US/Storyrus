"""Tabela de preço e conversão usage -> USD.

Valores default vêm de Settings (env). Sem rede: só aritmética local.
"""

from __future__ import annotations

from typing import Any

from app.config import settings


def _f(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def openai_image_cost(usage: dict | None = None) -> float:
    """Custo de uma geracao GPT Image (flat; usage reservado para tabela futura)."""
    _ = usage
    return round(settings.price_openai_image_usd, 6)


def _unit_image_usd() -> float:
    return float(settings.price_openai_image_usd)


def image_cost(usage: dict | None = None) -> float:
    """Compat: custo de imagem = GPT Image flat (usage ignorado)."""
    return openai_image_cost(usage)


def text_cost(usage: dict | None = None) -> float:
    """Custo Claude a partir do bloco `usage` da Messages API."""
    usage = usage or {}
    inp = _f(usage.get("input_tokens", usage.get("inputTokens")))
    out = _f(usage.get("output_tokens", usage.get("outputTokens")))
    if not inp and not out:
        return 0.0
    total = (
        inp / 1_000_000 * settings.price_claude_input_per_mtok
        + out / 1_000_000 * settings.price_claude_output_per_mtok
    )
    return round(total, 6)


def video_cost(duration_s: float | None) -> float:
    """Custo Kling: segundos faturáveis × preço por segundo."""
    seconds = max(_f(duration_s), 0.0)
    return round(seconds * settings.price_kling_per_second_usd, 6)


def add_usd(*values: float | None) -> float:
    """Soma custos parciais (None = 0)."""
    return round(sum(_f(v) for v in values), 6)


def estimate_job_usd(job_type: str | Any) -> float:
    """Estimativa local (sem rede) do burn USD de um job, para teto diario.

    Conservadora o bastante para bloquear antes do vendor; nao e cobranca.
    Avatar/cena incluem 1 geracao + 1 refine tipico.
    """
    raw = getattr(job_type, "value", job_type)
    t = str(raw or "").upper()
    img = _unit_image_usd()

    if t in ("AVATAR", "REALISTIC", "EXTRA_CHARACTER"):
        return round(img * 2.0, 6)
    if t == "STORYBOARD":
        return round(img * 2.0, 6)
    if t == "STORY":
        # Claude curto: ~ordem de alguns centavos.
        return 0.05
    if t == "EBOOK":
        pages = max(int(settings.ebook_pages or 1), 1)
        factor = 2.0 if (settings.ebook_face_match and settings.ebook_refine_scene) else 1.25
        return round(pages * img * factor, 6)
    if t == "VIDEO":
        return video_cost(settings.default_video_duration_s)
    if t == "NARRATED_VIDEO":
        return round(video_cost(settings.default_video_duration_s) + 0.05, 6)
    return round(img, 6)
