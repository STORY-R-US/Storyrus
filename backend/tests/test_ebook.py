"""Testes da diagramação especial das páginas do ebook."""

from io import BytesIO

from PIL import Image
from pypdf import PdfReader

from app.workers.ebook import (
    _name_page_parts,
    _split_story_caption,
    build_pdf,
    cover_palette_for,
    split_cover_title,
)

NAME_TEXT = (
    "Matteo se soletra assim: M · A · T · T · E · O.\n"
    "Matteo, menino valente, caminha com a gente.\n"
    "M é magia. A é amigo. T é terno. T é talentoso. "
    "E é especial. O é ousado."
)


def _image_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (1024, 1024), (91, 126, 83)).save(buf, format="PNG")
    return buf.getvalue()


def test_split_cover_title_strips_name_and_glue():
    assert split_cover_title("Lia e o Fundo do Mar", "Lia") == ("Lia", "O Fundo do Mar")
    assert split_cover_title("Matteo na Amazônia — Alfabeto dos Animais", "Matteo") == (
        "Matteo",
        "Na Amazônia — Alfabeto dos Animais",
    )
    assert split_cover_title("O atacante Matteo", "Matteo") == ("Matteo", "O atacante")
    assert split_cover_title("As aventuras de Matteo e Dino", "Matteo") == (
        "Matteo",
        "As aventuras e Dino",
    )
    assert split_cover_title("Sofia and the Enchanted Forest", "Sofia") == (
        "Sofia",
        "The Enchanted Forest",
    )
    assert split_cover_title("A Minha Grande Aventura", None) == (
        "",
        "A Minha Grande Aventura",
    )


def test_cover_palette_for_template_and_theme():
    ocean = cover_palette_for("mergulho_mar")
    assert ocean["stroke"] == "#2b7eb5"
    forest = cover_palette_for("reino_animais")
    assert forest["stroke"] == "#4a6b3a"
    dino = cover_palette_for(None, "dinosaurs")
    assert dino["stroke"] == "#c47a2a"
    default = cover_palette_for()
    assert default["stroke"] == "#2a3d6b"


def test_cover_page_separates_name_and_story_title():
    blob = build_pdf(
        title="Matteo na Amazônia — Alfabeto dos Animais",
        pages=[{"text": "Uma floresta quieta.", "image": _image_bytes(), "layout": "story"}],
        child_name="Matteo",
        preview_pages=None,
        cover_palette=cover_palette_for("alfabeto_amazonia"),
    )
    cover = PdfReader(BytesIO(blob)).pages[0]
    extracted = " ".join((cover.extract_text() or "").split())
    assert "Matteo" in extracted
    assert "Amazônia" in extracted or "Amazonia" in extracted
    assert "Alfabeto" in extracted


def test_name_page_parts_preserve_complete_acrostic():
    heading, spelled, role, qualities = _name_page_parts(NAME_TEXT)

    assert heading == "Matteo se soletra assim:"
    assert spelled == "M · A · T · T · E · O."
    assert role == "Matteo, menino valente, caminha com a gente."
    assert qualities == [
        "M é magia.",
        "A é amigo.",
        "T é terno.",
        "T é talentoso.",
        "E é especial.",
        "O é ousado.",
    ]


def test_name_layout_renders_acrostic_inside_left_panel():
    blob = build_pdf(
        title="Matteo na Amazônia",
        pages=[{"text": NAME_TEXT, "image": _image_bytes(), "layout": "name"}],
        child_name="",
        preview_pages=None,
    )
    reader = PdfReader(BytesIO(blob))
    page = next(p for p in reader.pages if "soletra assim" in (p.extract_text() or ""))
    extracted = page.extract_text() or ""
    normalized = " ".join(extracted.split())

    for fragment in (
        "Matteo se soletra assim:",
        "M · A · T · T · E · O.",
        "Matteo, menino valente, caminha com a gente.",
        "M",
        "é magia.",
        "O",
        "é ousado.",
    ):
        assert fragment in normalized

    positions: list[float] = []

    def collect_position(text, _cm, tm, _font, _size):
        if any(marker in text for marker in ("soletra", "magia", "amigo", "terno", "ousado")):
            positions.append(float(tm[4]))

    page.extract_text(visitor_text=collect_position)
    assert positions
    assert max(positions) < 310


STORY_WITH_FACT = (
    "A BORBOLETA voava leve, cheia de cor e beleza.\n"
    "Suas asas delicadas enfeitavam toda a natureza.\n\n"
    "Aprendendo mais: A borboleta tem asas coloridas e gosta de flores."
)


def test_split_story_caption_separates_fact_block():
    verse, fact = _split_story_caption(STORY_WITH_FACT)
    assert verse.startswith("A BORBOLETA")
    assert "Aprendendo mais:" in fact
    assert "Aprendendo mais:" not in verse


def _story_page(reader: PdfReader, marker: str):
    return next(p for p in reader.pages if marker in (p.extract_text() or ""))


def test_story_caption_sits_on_lower_third_and_fact_is_smaller():
    blob = build_pdf(
        title="Matteo no Reino",
        pages=[{"text": STORY_WITH_FACT, "image": _image_bytes(), "layout": "story"}],
        child_name="",
        preview_pages=None,
    )
    page = _story_page(PdfReader(BytesIO(blob)), "BORBOLETA")
    extracted = " ".join((page.extract_text() or "").split())
    assert "A BORBOLETA voava leve" in extracted
    assert "Aprendendo mais:" in extracted
    assert "borboleta tem asas coloridas" in extracted

    verse_y: list[float] = []
    fact_y: list[float] = []
    verse_size: list[float] = []
    fact_size: list[float] = []

    def collect(text, _cm, tm, _font, size):
        y = float(tm[5])
        if "BORBOLETA" in text or "asas delicadas" in text:
            verse_y.append(y)
            verse_size.append(float(size))
        if "Aprendendo" in text or "coloridas" in text:
            fact_y.append(y)
            fact_size.append(float(size))

    page.extract_text(visitor_text=collect)
    assert verse_y and fact_y
    assert max(verse_y) < 310
    assert min(verse_y) > 70
    assert max(fact_y) < 310
    assert max(fact_size) < min(verse_size)


def test_story_caption_honors_top_text_band():
    blob = build_pdf(
        title="Matteo no Reino",
        pages=[
            {
                "text": "Matteo acordou bem cedo, contente para passear.",
                "image": _image_bytes(),
                "layout": "story",
                "text_band": "top",
            }
        ],
        child_name="",
        preview_pages=None,
    )
    page = _story_page(PdfReader(BytesIO(blob)), "acordou bem cedo")
    ys: list[float] = []

    def collect(text, _cm, tm, _font, _size):
        if "acordou" in text or "passear" in text:
            ys.append(float(tm[5]))

    page.extract_text(visitor_text=collect)
    assert ys
    assert min(ys) > 310
