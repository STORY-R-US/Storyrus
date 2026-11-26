"""Livros novos com 20 páginas; os criados antes continuam com 16."""

import uuid

import pytest
import test_master_book as master

from app.ai_clients.base import TextResult
from app.config import settings
from app.models import Project
from app.services import book_profile
from app.workers import book_render, handlers

# Fixture e auxiliares da suíte do Estúdio.
studio = master.studio
_png = master._png
_run = master._run


@pytest.fixture
def twenty_pages(monkeypatch):
    monkeypatch.setattr(settings, "book_pages", 20)


def test_books_without_page_count_keep_sixteen_pages():
    class Saved:
        book_profile = {"version": book_profile.VERSION, "current_page": 3}

    class Legacy:
        book_profile = None

    assert book_profile.page_count(Saved()) == 16
    assert book_profile.page_count(Legacy()) == 16


@pytest.mark.asyncio
async def test_new_book_is_written_with_twenty_pages(twenty_pages, studio, monkeypatch):
    client, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    assert project.book_profile["page_count"] == 20
    asked = []

    class Text:
        async def generate_story(self, **kwargs):
            asked.append(kwargs)
            text = "Título: Lia e as estrelas\n\n" + "\n\n".join(
                f"Página {i}:\nVerso {i}." for i in range(1, 21)
            )
            return TextResult(text=text, cost_usd=0, meta={})

        async def moderate_book_input(self, **kwargs):
            return TextResult(text='{"flagged":false}', cost_usd=0, meta={"flagged": False})

    book_profile.update(
        project,
        stage="preview_ready",
        costume="azul",
        locales={"pt-BR": {"title": "Lia e as estrelas"}},
    )
    db.commit()
    monkeypatch.setattr(settings, "offline_fallback", False)
    monkeypatch.setattr(settings, "skip_openai", False)
    monkeypatch.setattr(handlers, "get_text_provider", lambda *a, **k: Text())
    await _run(studio, "story")
    project = db.get(Project, uuid.UUID(pid))
    assert asked and asked[0]["pages"] == 20
    assert "EXATAMENTE 20 paginas" in asked[0]["brief"]
    assert project.book_profile["stories"]["pt-BR"].count("Página") == 20
    # Página 20 existe; a 21 não.
    too_far = client.post(f"/v1/projects/{pid}/story", json={"page": 21, "brief": "Mais luz"})
    assert too_far.status_code == 422


def test_sixteen_page_book_refuses_page_twenty(studio):
    client, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    assert book_profile.page_count(project) == 16
    book_profile.update(project, stage="story_ready")
    db.commit()
    response = client.post(f"/v1/projects/{pid}/story", json={"page": 20, "brief": "Mais luz"})
    assert response.status_code == 422


def test_print_pdf_takes_sixteen_or_twenty_pages():
    page = _png()
    for total in (16, 20):
        assert book_render.pdf(page, [page] * total, page, size_cm=20)
    with pytest.raises(ValueError):
        book_render.pdf(page, [page] * 18, page, size_cm=20)


def test_print_pdf_aceita_paginas_lidas_uma_a_uma():
    """A montagem final lê cada página só quando vai gravá-la no PDF."""
    page = _png()
    read = []

    def lazy():
        for number in range(20):
            read.append(number)
            yield page

    pages = lazy()
    assert read == []
    blob = book_render.pdf(page, pages, page, size_cm=20, page_count=20)
    assert blob.startswith(b"%PDF")
    assert read == list(range(20))
    with pytest.raises(ValueError):
        book_render.pdf(page, iter([page] * 18), page, size_cm=20, page_count=18)
