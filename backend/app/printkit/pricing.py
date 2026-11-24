"""Tabela do impresso, dos extras digitais e da compra só digital.

Desde 24/11/2026 o 20×20 tem um valor por capa: dura R$ 329 e flexível R$ 309.
"""

from __future__ import annotations

from typing import Any

from app.config import settings

# Livro de prova da vitrine. O Stripe recusa cobrança em BRL abaixo de R$ 0,50.
TEST_BOOK_THEME = "livro_teste"
TEST_BOOK_CENTS = 50

PRINT = "print"
DIGITAL = "digital"


def book_price_cents(
    book_size: str | None, theme: str | None = None, cover_type: str | None = None
) -> int:
    if book_size not in {"P", "M"}:
        raise ValueError(book_size or "")
    if theme == TEST_BOOK_THEME:
        return TEST_BOOK_CENTS
    if book_size == "P":
        return int(settings.print_price_p_cents)
    # Sem capa escolhida, vale o valor da capa dura (o maior), nunca abaixo do real.
    if cover_type == "soft":
        return int(settings.print_price_soft_cents)
    return int(settings.print_price_hard_cents)


def cover_prices(theme: str | None = None) -> dict:
    """Valor do 20×20 em cada capa, para o checkout mostrar os dois."""
    return {
        "hard": book_price_cents("M", theme, "hard"),
        "soft": book_price_cents("M", theme, "soft"),
    }


def purchase_choice(project: Any) -> dict:
    """O que a família escolheu comprar. Sem escolha salva: só o impresso."""
    raw = ((getattr(project, "purchase_flow", None) or {}).get("purchase")) or {}
    fulfillment = raw.get("fulfillment") if raw.get("fulfillment") in {PRINT, DIGITAL} else PRINT
    ebook = bool(raw.get("ebook"))
    video = bool(raw.get("video"))
    if fulfillment == DIGITAL and not (ebook or video):
        ebook = True
    return {"fulfillment": fulfillment, "ebook": ebook, "video": video}


def is_digital(project: Any) -> bool:
    return purchase_choice(project)["fulfillment"] == DIGITAL


def ebook_delivered(project: Any) -> bool:
    """PDF liberado para a família.

    Pedidos pagos antes dos extras não têm escolha salva e continuam com o PDF,
    como prometido na compra.
    """
    if not ((getattr(project, "purchase_flow", None) or {}).get("purchase")):
        return True
    return purchase_choice(project)["ebook"]


def _tier(ebook: bool, video: bool, single_ebook: int, single_video: int, bundle: int) -> int:
    if ebook and video:
        return int(bundle)
    if ebook:
        return int(single_ebook)
    if video:
        return int(single_video)
    return 0


def extras_price_cents(ebook: bool, video: bool, theme: str | None = None) -> int:
    if theme == TEST_BOOK_THEME:
        return 0
    return _tier(
        ebook,
        video,
        settings.price_extra_ebook_cents,
        settings.price_extra_video_cents,
        settings.price_extra_bundle_cents,
    )


def digital_price_cents(ebook: bool, video: bool, theme: str | None = None) -> int:
    if not (ebook or video):
        raise ValueError("Escolha o e-book, a história animada ou os dois.")
    if theme == TEST_BOOK_THEME:
        return TEST_BOOK_CENTS
    return _tier(
        ebook,
        video,
        settings.price_digital_ebook_cents,
        settings.price_digital_video_cents,
        settings.price_digital_bundle_cents,
    )


def price_table(theme: str | None = None) -> dict:
    """Valores mostrados no checkout, sempre vindos do servidor."""
    return {
        "book": cover_prices(theme),
        "extra": {
            "ebook": extras_price_cents(True, False, theme),
            "video": extras_price_cents(False, True, theme),
            "bundle": extras_price_cents(True, True, theme),
        },
        "digital": {
            "ebook": digital_price_cents(True, False, theme),
            "video": digital_price_cents(False, True, theme),
            "bundle": digital_price_cents(True, True, theme),
        },
    }
