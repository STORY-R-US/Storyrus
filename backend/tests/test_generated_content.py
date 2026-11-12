import json

import pytest

from app.services import generated_content
from app.workers.handlers.common import _parse_pages


@pytest.mark.parametrize(
    "wrap", [lambda s: s, lambda s: "\ufeff" + s, lambda s: "```JSON\n" + s + "\n```", json.dumps]
)
def test_recovers_json_transport_format_without_changing_values(wrap):
    original = {"locales": {"pt-BR": {"title": "Lia", "left": "Um verso.\nOutro verso."}}}
    assert generated_content.object_from_text(wrap(json.dumps(original))) == original


@pytest.mark.parametrize("value", ['{"locales":', "{} {}", "[{}]", 'explanation {"a": 1}'])
def test_incomplete_or_ambiguous_json_is_not_invented(value):
    with pytest.raises(ValueError):
        generated_content.object_from_text(value)


@pytest.mark.parametrize(
    "alias,language",
    [("pt", "pt-BR"), ("pt_br", "pt-BR"), ("PT-BR", "pt-BR"), ("ES", "es"), ("EN", "en")],
)
def test_alias_and_verse_array_recovery_preserve_words(alias, language):
    result = generated_content.normalize_locales(
        {"locales": {alias: {"title": "Lia", "left": ["Um verso.", "Outro verso."]}}}, [language]
    )
    assert list(result["locales"]) == [language]
    assert result["locales"][language]["left"] == "Um verso.\nOutro verso."


@pytest.mark.parametrize("locales", [{}, {"pt": {}, "PT_br": {}}, {"pt-BR": "invalid"}])
def test_missing_or_ambiguous_locales_fail_closed(locales):
    with pytest.raises(ValueError):
        generated_content.normalize_locales({"locales": locales}, ["pt-BR"])


@pytest.mark.parametrize(
    "heading",
    ["Página {n}:", "Pagina {n} -", "Page {n}:", "**Page {n}:**", "## Página {n}", "__Page {n}__"],
)
@pytest.mark.parametrize("title", ["Título: Lia", "Title: Lia", "## Title: Lia"])
def test_sixteen_pages_keep_all_words_in_all_heading_formats(heading, title):
    passages = [f"Verse {n} on its own page.\nSecond line {n}." for n in range(1, 17)]
    raw = (
        title
        + "\n\n"
        + "\n\n".join(heading.format(n=n) + "\n" + verse for n, verse in enumerate(passages, 1))
    )
    assert _parse_pages(raw) == passages
    assert _parse_pages("```markdown\n" + raw + "\n```") == passages


@pytest.mark.parametrize("numbers", [[1, 1, 2], [1, 3, 4], [2, 1, 3]])
def test_does_not_silently_renumber_broken_story(numbers):
    assert _parse_pages("\n".join(f"Page {n}: text {n}" for n in numbers)) == []


@pytest.mark.parametrize(
    "heading", ["Title: Lia", "**Title: Lia**", "**Title:** Lia", "Título: Lia"]
)
def test_title_markup_is_not_printed_as_part_of_title(heading):
    from app.workers.handlers.common import _parse_title

    assert _parse_title(heading + "\nPage 1: Story") == "Lia"
