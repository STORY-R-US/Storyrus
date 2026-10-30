"""Tabela do impresso. A capa não altera o valor, como na vitrine."""

from __future__ import annotations

from app.config import settings

# Livro de prova da vitrine. O Stripe recusa cobrança em BRL abaixo de R$ 0,50.
TEST_BOOK_THEME = "livro_teste"
TEST_BOOK_CENTS = 50


def book_price_cents(book_size: str | None, theme: str | None = None) -> int:
    if book_size not in {"P", "M"}:
        raise ValueError(book_size or "")
    if theme == TEST_BOOK_THEME:
        return TEST_BOOK_CENTS
    if book_size == "P":
        return int(settings.print_price_p_cents)
    return int(settings.print_price_m_cents)
