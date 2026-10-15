"""Tabela do impresso. A capa não altera o valor, como na vitrine."""

from __future__ import annotations

from app.config import settings


def book_price_cents(book_size: str | None) -> int:
    if book_size == "P":
        return int(settings.print_price_p_cents)
    if book_size == "M":
        return int(settings.print_price_m_cents)
    raise ValueError(book_size or "")
