"""Montagem do ebook como livro infantil ilustrado premium (estilo WonderWraps).

build_pdf gera um PDF QUADRADO (formato dos livros personalizados impressos) com:
  1. capa em sangria total com o titulo (nome da crianca em destaque) + selo da marca;
  2. pagina-poema de abertura ("Para todos os pequenos aventureiros...");
  3. pagina "Feito especialmente para {NOME}" com retrato do personagem em moldura;
  4. dedicatoria opcional dos pais;
  5. paginas da historia em sangria total com a estrofe mesclada na arte;
  6. contracapa com poema de encerramento em moldura + selo;
  7. pagina final "Obrigado".
Usa reportlab (puro Python, sem deps de sistema).
Fonte: Megifera Indica.
"""  # layout v3 — Megifera Indica + capa redesenhada + preview limitado

from __future__ import annotations

import base64
import html
import io
import logging
import math
import os
import unicodedata
from pathlib import Path

logger = logging.getLogger("ebook")

# ------------------------------------------------------------------- fontes
# Fonte oficial do ebook: Megifera Indica (Risma Type).
# Os TTFs sao gerados no build por backend/scripts/fetch_fonts.py.
_FALLBACK_FONTS = {
    "body": "Times-Bold",
    "italic": "Times-Italic",
    "brand": "Helvetica-Bold",
    "cover_name": "Times-Bold",
    "cover_story": "Helvetica-Bold",
}
_fonts_cache: dict | None = None


def _fonts_dir() -> Path | None:
    candidates = [
        os.environ.get("EBOOK_FONTS_DIR"),
        Path(__file__).resolve().parents[1] / "assets" / "fonts",
        Path("app/assets/fonts"),
    ]
    for cand in candidates:
        if cand and Path(cand).is_dir():
            return Path(cand)
    return None


def _fonts() -> dict:
    """Registra a Andika no reportlab (uma unica vez) e devolve o mapa.

    Andika (SIL International, OFL) e a fonte oficial do ebook: legivel,
    licenca livre para redistribuicao, e os TTFs ficam versionados em
    app/assets/fonts/ (sem depender de download em build, ao contrario da
    Megifera Indica anterior)."""
    global _fonts_cache
    if _fonts_cache is not None:
        return _fonts_cache
    fonts = dict(_FALLBACK_FONTS)
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        base = _fonts_dir()
        regular = base / "Andika-Regular.ttf" if base else None
        bold = base / "Andika-Bold.ttf" if base else None
        italic = base / "Andika-Italic.ttf" if base else None
        if regular and regular.exists():
            pdfmetrics.registerFont(TTFont("Andika", str(regular)))
            fonts["body"] = "Andika"
            if bold and bold.exists():
                pdfmetrics.registerFont(TTFont("Andika-Bold", str(bold)))
                fonts["brand"] = "Andika-Bold"
            else:
                fonts["brand"] = "Andika"
            if italic and italic.exists():
                pdfmetrics.registerFont(TTFont("Andika-Italic", str(italic)))
                fonts["italic"] = "Andika-Italic"
            else:
                fonts["italic"] = "Andika"
            logger.info("Fonte do ebook: Andika (%s)", base)
        else:
            logger.warning("Andika-Regular.ttf nao encontrada em %s; usando fontes fallback.", base)
        playfair = base / "PlayfairDisplay-Regular.ttf" if base else None
        fredoka = base / "Fredoka-Bold.ttf" if base else None
        if playfair and playfair.exists():
            pdfmetrics.registerFont(TTFont("PlayfairDisplay", str(playfair)))
            fonts["cover_name"] = "PlayfairDisplay"
        if fredoka and fredoka.exists():
            pdfmetrics.registerFont(TTFont("Fredoka-Bold", str(fredoka)))
            fonts["cover_story"] = "Fredoka-Bold"
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falha ao registrar fontes do ebook (%s); usando fontes fallback", exc)
    _fonts_cache = fonts
    return fonts


CREAM = (1.0, 0.972, 0.936)
SKY = (0.878, 0.933, 1.0)
NAVY = (0.106, 0.184, 0.373)
GOLD = (0.956, 0.718, 0.251)
CORAL = (0.937, 0.561, 0.294)
LEAF = (0.494, 0.633, 0.420)
INK = (0.20, 0.23, 0.28)

_COVER_FILL = "#fffaf2"
_COVER_CREAM = "#f4ead4"
COVER_PALETTES: dict[str, dict[str, str]] = {
    "ocean": {"name": "#16324f", "fill": _COVER_FILL, "stroke": "#2b7eb5"},
    "forest": {"name": _COVER_CREAM, "fill": _COVER_FILL, "stroke": "#4a6b3a"},
    "dino": {"name": _COVER_CREAM, "fill": _COVER_FILL, "stroke": "#c47a2a"},
    "circus": {"name": _COVER_CREAM, "fill": _COVER_FILL, "stroke": "#c45a6a"},
    "orchard": {"name": _COVER_CREAM, "fill": _COVER_FILL, "stroke": "#c45a3a"},
    "default": {"name": "#1a2748", "fill": _COVER_FILL, "stroke": "#2a3d6b"},
}
_TEMPLATE_PALETTE = {
    "mergulho_mar": "ocean",
    "reino_animais": "forest",
    "alfabeto_amazonia": "forest",
    "alfabeto_frutas": "orchard",
}
_THEME_PALETTE = {
    "underwater": "ocean",
    "fantasy": "forest",
    "dinosaurs": "dino",
    "adventure": "circus",
}
_NAME_GLUE = {"e", "and", "y", "de"}


def cover_palette_for(template_id: str | None = None, theme: str | None = None) -> dict[str, str]:
    """Paleta da capa (nome / fill / stroke) a partir do template ou tema."""
    key = _TEMPLATE_PALETTE.get((template_id or "").strip())
    if not key:
        key = _THEME_PALETTE.get((theme or "").strip().lower(), "default")
    return dict(COVER_PALETTES[key])


def _hex_rgb(value: str) -> tuple[float, float, float]:
    raw = (value or "").lstrip("#")
    if len(raw) != 6:
        return NAVY
    return tuple(int(raw[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


def _luma(rgb: tuple[float, float, float]) -> float:
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _cap_first(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return text
    return text[0].upper() + text[1:]


def _strip_name_glue(words: list[str], *, leading: bool) -> list[str]:
    out = list(words)
    if leading:
        while out and out[0].lower().rstrip(".,;:") in _NAME_GLUE:
            out.pop(0)
    else:
        while out and out[-1].lower().rstrip(".,;:") in _NAME_GLUE:
            out.pop()
    return out


def split_cover_title(title: str, child_name: str | None) -> tuple[str, str]:
    """Separa o nome da criança do título da aventura para a capa."""
    raw_title = (title or "").strip()
    name = (child_name or "").strip()
    if not raw_title:
        return name, ""
    if not name:
        return "", _cap_first(raw_title)
    idx = raw_title.upper().find(name.upper())
    if idx < 0:
        return name, _cap_first(raw_title)
    before = raw_title[:idx].strip(" ,-—–")
    after = raw_title[idx + len(name) :].strip(" ,-—–")
    before_words = before.split()
    after_words = after.split()
    if not before_words:
        story = " ".join(_strip_name_glue(after_words, leading=True))
    elif not after_words:
        story = " ".join(_strip_name_glue(before_words, leading=False))
    else:
        story = " ".join(
            part
            for part in (
                " ".join(_strip_name_glue(before_words, leading=False)),
                after,
            )
            if part
        )
    return name, _cap_first(story or raw_title)


# Textos fixos por idioma (padrão dos livros de referência).
STRINGS = {
    "pt-BR": {
        "opening": (
            "Para todos os pequenos aventureiros,\n"
            "que seus coracoes sejam valentes,\n"
            "e que seus sonhos os levem a lugares\n"
            "incriveis e surpreendentes."
        ),
        "made_for": "Feito especialmente para",
        "blessing": (
            "Que a sua vida seja cheia de\n"
            "coragem, carinho e alegria!\n"
            "Que o seu sempre te leve\n"
            "a amar, proteger e explorar\n"
            "as maravilhas do mundo."
        ),
        "closing": (
            "De florestas a oceanos, e ceus a brilhar,\n"
            "esta grande aventura foi movida pelo amar.\n"
            "Para cada pequeno sonhador de coracao valente,\n"
            "o mundo e seu amigo — siga sonhando em frente."
        ),
        "closing_named": (
            "De florestas a oceanos, e ceus a brilhar,\n"
            "a aventura de {name} foi movida pelo amar.\n"
            "Para cada pequeno sonhador de coracao valente,\n"
            "o mundo e seu amigo — siga sonhando em frente."
        ),
        "thanks": "Obrigado",
        "with_love": "com amor",
        "tagline": "um livro personalizado",
        "preview_title": "Este e um preview",
        "preview_msg": (
            "Este PDF contem apenas {shown} das {total} paginas da historia.\n"
            "Para ter o livro completo, finalize a compra."
        ),
    },
    "en": {
        "opening": (
            "To all the little adventurers,\n"
            "may your hearts be brave,\n"
            "and your dreams take you places,\n"
            "wild and wonderfully paved."
        ),
        "made_for": "Created especially for",
        "blessing": (
            "May your life be filled\n"
            "with courage, kindness, and joy!\n"
            "May your heart always lead you\n"
            "to protect, love, and explore\n"
            "the wonders of the world."
        ),
        "closing": (
            "From forests to oceans, and skies up above,\n"
            "this great adventure was powered by love.\n"
            "For every young dreamer, whose heart beats strong,\n"
            "the world is your friend, so dream and belong."
        ),
        "closing_named": (
            "From forests to oceans, and skies up above,\n"
            "{name}'s great adventure was powered by love.\n"
            "For every young dreamer, whose heart beats strong,\n"
            "the world is your friend, so dream and belong."
        ),
        "thanks": "Thank you",
        "with_love": "with love",
        "tagline": "a personalized book",
        "preview_title": "This is a preview",
        "preview_msg": (
            "This PDF contains only {shown} of {total} story pages.\n"
            "To get the complete book, please complete your purchase."
        ),
    },
}


def _strings(language: str | None) -> dict:
    return STRINGS["en"] if (language or "").lower().startswith("en") else STRINGS["pt-BR"]


def _win(s: str) -> str:
    """Garante texto renderizavel pelas fontes padrao do PDF (WinAnsi/cp1252).

    Acentos do portugues (a-til, cedilha etc.) SAO suportados e preservados;
    apenas caracteres fora do cp1252 (emoji, simbolos raros) sao aproximados.
    """
    out: list[str] = []
    for ch in s or "":
        try:
            ch.encode("cp1252")
            out.append(ch)
        except UnicodeEncodeError:
            out.append(unicodedata.normalize("NFKD", ch).encode("ascii", "ignore").decode())
    return "".join(out)


_FACT_MARKERS = ("Aprendendo mais:", "Learning more:")


def _split_story_caption(text: str) -> tuple[str, str]:
    """Separa o verso do bloco educacional ('Aprendendo mais')."""
    raw = (text or "").replace("\r\n", "\n").strip()
    if not raw:
        return "", ""
    verse, sep, fact = raw.partition("\n\n")
    if sep:
        return verse.strip(), fact.strip()
    for marker in _FACT_MARKERS:
        idx = raw.find(marker)
        if idx > 0:
            return raw[:idx].strip(), raw[idx:].strip()
        if idx == 0:
            return "", raw.strip()
    return raw, ""


def _name_page_parts(text: str) -> tuple[str, str, str, list[str]]:
    """Separa o acróstico da P2 sem alterar suas palavras."""
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return "", "", "", []

    heading = lines[0]
    spelled = ""
    if ":" in heading:
        heading, spelled = heading.split(":", 1)
        heading = f"{heading.strip()}:"
        spelled = spelled.strip()

    role = lines[1] if len(lines) > 1 else ""
    quality_blob = " ".join(lines[2:]).strip()
    qualities = [f"{part.strip()}." for part in quality_blob.split(".") if part.strip()]
    return heading, spelled, role, qualities


def _img_tag(image_bytes: bytes | None, mime: str = "image/png") -> str:
    if not image_bytes:
        return ""
    b64 = base64.b64encode(image_bytes).decode()
    return f'<img class="page-img" src="data:{mime};base64,{b64}"/>'


def build_html(title: str, pages: list[dict]) -> str:
    blocks = [
        f'<section class="page">{_img_tag(p.get("image"), p.get("mime", "image/png"))}'
        f"<p>{html.escape(p.get('text', ''))}</p></section>"
        for p in pages
    ]
    return (
        '<!doctype html><meta charset="utf-8"><title>' + html.escape(title) + "</title>"
        "<style>body{font-family:'Segoe UI',sans-serif}</style>"
        "<h1>" + html.escape(title) + "</h1>" + "".join(blocks)
    )


def render_pdf(html_str: str) -> tuple[bytes, str]:
    try:
        from weasyprint import HTML  # type: ignore

        return HTML(string=html_str).write_pdf(), "application/pdf"
    except Exception as exc:  # noqa: BLE001
        logger.warning("WeasyPrint indisponivel (%s); entregando HTML", exc)
        return html_str.encode("utf-8"), "text/html"


def build_pdf(
    title: str,
    pages: list[dict],
    cover: bytes | None = None,
    dedication: str | None = None,
    portrait: bytes | None = None,
    child_name: str | None = None,
    language: str | None = "pt-BR",
    extra_characters: list[dict] | None = None,
    preview_pages: int | None = 3,
    cover_palette: dict[str, str] | None = None,
    page_cm: float | None = None,
) -> bytes:
    from reportlab.lib.utils import ImageReader, simpleSplit
    from reportlab.pdfgen import canvas

    tr = _strings(language)
    name = (child_name or "").strip()
    F = _fonts()  # Raleway Light 300 (fallback: fontes base do PDF)

    # Miolo desenhado em 612 pt. M = 20 cm e P = 15 cm só mudam a escala da página.
    W = H = 612.0
    side = W if not page_cm else page_cm * 72.0 / 2.54
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(side, side))

    def fit_page() -> None:
        if side != W:
            c.scale(side / W, side / W)

    fit_page()

    # ------------------------------------------------------------------ utils
    def bg(color):
        c.setFillColorRGB(*color)
        c.rect(0, 0, W, H, fill=1, stroke=0)

    def reader(b):
        try:
            return ImageReader(io.BytesIO(b)) if b else None
        except Exception:  # noqa: BLE001
            return None

    def full_bleed(ir):
        """Imagem cobrindo a pagina inteira (sangria), cortando o excesso."""
        iw, ih = ir.getSize()
        s = max(W / iw, H / ih)
        dw, dh = iw * s, ih * s
        c.drawImage(ir, (W - dw) / 2, (H - dh) / 2, dw, dh, preserveAspectRatio=False, mask="auto")

    def star(cx, cy, r, color=GOLD, alpha=1.0):
        c.setFillAlpha(alpha)
        c.setFillColorRGB(*color)
        p = c.beginPath()
        for i in range(10):
            ang = math.pi / 2 + i * math.pi / 5
            rr = r if i % 2 == 0 else r * 0.45
            (p.moveTo if i == 0 else p.lineTo)(cx + rr * math.cos(ang), cy + rr * math.sin(ang))
        p.close()
        c.drawPath(p, fill=1, stroke=0)
        c.setFillAlpha(1)

    def flower(cx, cy, r, color=CORAL):
        """Florzinha decorativa simples (5 petalas + miolo)."""
        c.setFillColorRGB(*color)
        for i in range(5):
            ang = i * 2 * math.pi / 5 + math.pi / 2
            c.circle(
                cx + r * 0.8 * math.cos(ang),
                cy + r * 0.8 * math.sin(ang),
                r * 0.55,
                fill=1,
                stroke=0,
            )
        c.setFillColorRGB(*GOLD)
        c.circle(cx, cy, r * 0.42, fill=1, stroke=0)

    def leaf(cx, cy, r, ang, color=LEAF):
        c.saveState()
        c.translate(cx, cy)
        c.rotate(ang)
        c.setFillColorRGB(*color)
        p = c.beginPath()
        p.moveTo(0, 0)
        p.curveTo(r * 0.6, r * 0.45, r * 1.4, r * 0.35, r * 2.0, 0)
        p.curveTo(r * 1.4, -r * 0.35, r * 0.6, -r * 0.45, 0, 0)
        p.close()
        c.drawPath(p, fill=1, stroke=0)
        c.restoreState()

    def corner_flourish(cx, cy, flip_x, flip_y):
        """Ramo floral de canto (paginas cerimoniais), estilo das referencias."""
        c.saveState()
        c.translate(cx, cy)
        c.scale(flip_x, flip_y)
        c.setStrokeColorRGB(*LEAF)
        c.setLineWidth(2.2)
        p = c.beginPath()
        p.moveTo(6, 84)
        p.curveTo(10, 44, 26, 20, 78, 8)
        c.drawPath(p, fill=0, stroke=1)
        leaf(14, 62, 8, 20)
        leaf(24, 40, 9, 35)
        leaf(46, 20, 9, 10)
        flower(10, 86, 7)
        flower(72, 10, 6, GOLD)
        c.restoreState()

    def split_lines(text, font, size, max_w):
        """Respeita quebras de linha do texto (versos) e re-quebra o que exceder."""
        lines: list[str] = []
        for raw in (_win(text or "")).splitlines():
            raw = raw.strip()
            if not raw:
                continue
            lines.extend(simpleSplit(raw, font, size, max_w))
        return lines

    def overlay(text, font, size, leading, side, bottom=None, top=None, center_x=None):
        """Texto mesclado na arte: branco limpo como na capa, SEM faixa preta.

        Contorno fino + sombra leve so para legibilidade sobre a ilustracao.
        Preserva os versos. Ancora pela base (bottom) ou topo (top).
        """
        cx = center_x if center_x is not None else W / 2
        lines = split_lines(text, font, size, W - 2 * side)
        if not lines:
            return 0
        h = len(lines) * leading
        ytop = (H - top - size) if top is not None else (bottom + h - leading)
        # contorno fino (estilo capa: branco legivel, sem bloco/halo grosso)
        outline = (0.08, 0.10, 0.18)
        c.setFont(font, size)
        y = ytop
        for ln in lines:
            x = cx - c.stringWidth(ln, font, size) / 2
            c.setFillColorRGB(*outline)
            for dx, dy in (
                (-1.2, 0),
                (1.2, 0),
                (0, -1.2),
                (0, 1.2),
                (-0.9, -0.9),
                (0.9, -0.9),
                (-0.9, 0.9),
                (0.9, 0.9),
            ):
                c.drawString(x + dx, y + dy, ln)
            c.setFillColorRGB(1, 1, 1)
            c.drawString(x, y, ln)
            y -= leading
        return h

    def brand_badge(y=34):
        c.setFillAlpha(0.92)
        c.setFillColorRGB(*NAVY)
        c.roundRect(W / 2 - 112, y, 224, 40, 20, fill=1, stroke=0)
        c.setFillAlpha(1)
        c.setFillColorRGB(1, 1, 1)
        c.setFont(F["brand"], 13)
        c.drawCentredString(W / 2, y + 22, "Story R Us")
        c.setFillColorRGB(*GOLD)
        c.setFont(F["italic"], 10.5)
        c.drawCentredString(W / 2, y + 8, _win(tr["tagline"]))

    def poem_panel(
        text, y_center, panel_w=W * 0.78, font=F["italic"], size=15.5, leading=24, framed=True
    ):
        """Poema centralizado num painel claro com moldura fina (estilo referencia)."""
        lines = split_lines(text, font, size, panel_w - 60)
        ph = len(lines) * leading + 56
        x0, y0 = (W - panel_w) / 2, y_center - ph / 2
        if framed:
            c.setFillColorRGB(1, 1, 1)
            c.setFillAlpha(0.88)
            c.roundRect(x0, y0, panel_w, ph, 14, fill=1, stroke=0)
            c.setFillAlpha(1)
            c.setStrokeColorRGB(*GOLD)
            c.setLineWidth(1.6)
            c.roundRect(x0 + 7, y0 + 7, panel_w - 14, ph - 14, 10, fill=0, stroke=1)
        c.setFillColorRGB(*INK)
        c.setFont(font, size)
        y = y0 + ph - 40
        for ln in lines:
            c.drawCentredString(W / 2, y, ln)
            y -= leading
        return y0, ph

    def draw_ink_lines(lines, font, size, leading, y):
        """Verso em tinta, centralizado, sem caixa e sem contorno."""
        c.setFillColorRGB(*INK)
        c.setFont(font, size)
        for ln in lines:
            c.drawCentredString(W / 2, y, ln)
            y -= leading
        return y

    def story_caption(text, band="bottom"):
        """Estrofe em tinta na arte: terço inferior, fato educacional menor."""
        verse, fact = _split_story_caption(text)
        if not verse and not fact:
            return 0
        max_h = H * 0.28
        side, gap = 48.0, 10.0
        verse_font, fact_font = F["brand"], F["italic"]
        verse_size, verse_leading = 16.5, 22.0
        fact_size, fact_leading = 11.5, 15.0
        content_w = W - 2 * side
        floor = H * 0.16

        def measure(v_size, v_lead, f_size, f_lead):
            v_lines = split_lines(verse, verse_font, v_size, content_w) if verse else []
            f_lines = split_lines(fact, fact_font, f_size, content_w) if fact else []
            h = 0.0
            if v_lines:
                h += len(v_lines) * v_lead
            if v_lines and f_lines:
                h += gap
            if f_lines:
                h += len(f_lines) * f_lead
            return v_lines, f_lines, h

        v_lines, f_lines, h = measure(verse_size, verse_leading, fact_size, fact_leading)
        while h > max_h and (verse_size > 12 or fact_size > 9):
            if verse_size > 12:
                verse_size -= 0.5
                verse_leading = max(16.0, verse_leading - 0.6)
            if fact_size > 9:
                fact_size -= 0.4
                fact_leading = max(12.0, fact_leading - 0.4)
            v_lines, f_lines, h = measure(verse_size, verse_leading, fact_size, fact_leading)

        first_lead = verse_leading if v_lines else fact_leading
        y = (H - 42 - verse_size) if band == "top" else (floor + h - first_lead)
        if v_lines:
            y = draw_ink_lines(v_lines, verse_font, verse_size, verse_leading, y)
        if v_lines and f_lines:
            y -= gap * 0.35
        if f_lines:
            draw_ink_lines(f_lines, fact_font, fact_size, fact_leading, y)
        return h

    def name_panel(text):
        """Painel botânico lateral da página do nome, fora do protagonista."""
        heading, spelled, role, qualities = _name_page_parts(text)
        x0, y0 = 22.0, 28.0
        panel_w, panel_h = W * 0.46, H - 56.0
        panel_top = y0 + panel_h
        center_x = x0 + panel_w / 2
        inset = 22.0
        content_w = panel_w - 2 * inset

        # Sombra, papel creme translúcido e moldura dupla.
        c.setFillColorRGB(*NAVY)
        c.setFillAlpha(0.18)
        c.roundRect(x0 + 5, y0 - 5, panel_w, panel_h, 22, fill=1, stroke=0)
        c.setFillColorRGB(*CREAM)
        c.setFillAlpha(0.94)
        c.roundRect(x0, y0, panel_w, panel_h, 22, fill=1, stroke=0)
        c.setFillAlpha(1)
        c.setStrokeColorRGB(*GOLD)
        c.setLineWidth(2.2)
        c.roundRect(x0, y0, panel_w, panel_h, 22, fill=0, stroke=1)
        c.setStrokeColorRGB(*LEAF)
        c.setLineWidth(0.8)
        c.roundRect(x0 + 8, y0 + 8, panel_w - 16, panel_h - 16, 16, fill=0, stroke=1)

        # Pequenos ramos nos cantos mantêm a linguagem visual do livro.
        leaf(x0 + 15, panel_top - 20, 6, -18, LEAF)
        leaf(x0 + 26, panel_top - 13, 5, -42, LEAF)
        flower(x0 + panel_w - 18, panel_top - 18, 4.5, CORAL)
        leaf(x0 + panel_w - 17, y0 + 17, 6, 162, LEAF)
        leaf(x0 + panel_w - 29, y0 + 12, 5, 142, LEAF)

        def fitted_size(value, font, maximum, minimum, max_width):
            value = _win(value)
            size = maximum
            while size > minimum and c.stringWidth(value, font, size) > max_width:
                size -= 0.5
            return max(minimum, size)

        y = panel_top - 48
        c.setFillColorRGB(*NAVY)
        c.setFont(F["italic"], 13.5)
        for line in split_lines(heading, F["italic"], 13.5, content_w):
            c.drawCentredString(center_x, y, line)
            y -= 18

        if spelled:
            y -= 7
            spelling_size = fitted_size(spelled, F["brand"], 24, 13, content_w)
            c.setFillColorRGB(*NAVY)
            c.setFont(F["brand"], spelling_size)
            c.drawCentredString(center_x, y, _win(spelled))
            y -= spelling_size + 15

        c.setStrokeColorRGB(*GOLD)
        c.setLineWidth(1.4)
        c.line(x0 + inset + 18, y, x0 + panel_w - inset - 18, y)
        star(center_x, y, 4.5, GOLD)
        y -= 28

        c.setFillColorRGB(*INK)
        role_size = 12.5
        c.setFont(F["italic"], role_size)
        for line in split_lines(role, F["italic"], role_size, content_w - 4):
            c.drawCentredString(center_x, y, line)
            y -= 17
        y -= 14

        if qualities:
            columns = 2 if len(qualities) > 1 else 1
            rows = math.ceil(len(qualities) / columns)
            gap_x, gap_y = 8.0, 9.0
            card_w = (content_w - gap_x) / 2 if columns == 2 else content_w
            available_h = y - (y0 + 42)
            card_h = min(45.0, (available_h - gap_y * (rows - 1)) / rows)
            card_h = max(32.0, card_h)

            for idx, quality in enumerate(qualities):
                col = idx % columns
                row = idx // columns
                card_x = x0 + inset + col * (card_w + gap_x)
                card_y = y - card_h - row * (card_h + gap_y)
                card_cy = card_y + card_h / 2

                c.setFillColorRGB(1, 1, 1)
                c.setFillAlpha(0.62)
                c.roundRect(card_x, card_y, card_w, card_h, 10, fill=1, stroke=0)
                c.setFillAlpha(1)
                c.setStrokeColorRGB(*GOLD)
                c.setLineWidth(0.8)
                c.roundRect(card_x, card_y, card_w, card_h, 10, fill=0, stroke=1)

                letter, _, description = quality.partition(" ")
                badge_x = card_x + 15
                c.setFillColorRGB(*GOLD)
                c.circle(badge_x, card_cy, 9, fill=1, stroke=0)
                c.setFillColorRGB(*NAVY)
                c.setFont(F["brand"], 8.8)
                c.drawCentredString(badge_x, card_cy - 3.1, _win(letter))

                description = description.strip()
                desc_size = fitted_size(description, F["body"], 10.5, 8.0, card_w - 37)
                c.setFillColorRGB(*INK)
                c.setFont(F["body"], desc_size)
                c.drawString(
                    card_x + 30,
                    card_cy - desc_size * 0.34,
                    _win(description),
                )

    # ------------------------------------------------------------- 1) CAPA ESTILIZADA
    palette = cover_palette or cover_palette_for()
    stroke_rgb = _hex_rgb(palette.get("stroke") or "#2a3d6b")
    fill_rgb = _hex_rgb(palette.get("fill") or _COVER_FILL)
    name_rgb = _hex_rgb(palette.get("name") or "#1a2748")
    if _luma(name_rgb) > 0.72:
        name_rgb = stroke_rgb
    wash = tuple(0.62 * 1.0 + 0.38 * ch for ch in stroke_rgb)
    sky_top = tuple(0.78 * 1.0 + 0.22 * ch for ch in stroke_rgb)

    pr_cov = reader(cover) or reader(portrait)
    bg(sky_top)
    c.setFillColorRGB(*sky_top)
    c.rect(0, H * 0.45, W, H * 0.55, fill=1, stroke=0)
    c.setFillColorRGB(*wash)
    c.rect(0, 0, W, H * 0.45, fill=1, stroke=0)
    for sx, sy, sr in (
        (52, H - 58, 9),
        (W - 58, H - 72, 7),
        (W * 0.22, H - 120, 5),
        (W * 0.78, H - 108, 6),
        (90, H - 180, 4),
        (W - 96, H - 190, 5),
    ):
        star(sx, sy, sr, GOLD, 0.85)

    cover_name, cover_story = split_cover_title(title, name)
    cover_name = _win(cover_name)
    cover_story = _win(cover_story)
    if cover_name:
        c.setFillColorRGB(*name_rgb)
        c.setFont(F["cover_name"], 30)
        c.drawCentredString(W / 2, H - 54, cover_name)

    if pr_cov:
        cx, cy, R = W / 2, H * 0.50, 148.0
        c.saveState()
        p = c.beginPath()
        p.circle(cx, cy, R)
        c.clipPath(p, stroke=0, fill=0)
        iw, ih = pr_cov.getSize()
        s = max((2 * R) / iw, (2 * R) / ih)
        dw, dh = iw * s, ih * s
        c.drawImage(
            pr_cov, cx - dw / 2, cy - dh / 2, dw, dh, preserveAspectRatio=False, mask="auto"
        )
        c.restoreState()
        c.setStrokeColorRGB(*stroke_rgb)
        c.setLineWidth(5)
        c.circle(cx, cy, R, fill=0, stroke=1)
        c.setStrokeColorRGB(1, 1, 1)
        c.setLineWidth(2)
        c.circle(cx, cy, R - 6, fill=0, stroke=1)

    if cover_story:
        story_font = F["cover_story"]
        max_w = W - 72
        story_size = 40.0
        story_lines = split_lines(cover_story, story_font, story_size, max_w)
        while story_size > 22 and len(story_lines) > 2:
            story_size -= 1.5
            story_lines = split_lines(cover_story, story_font, story_size, max_w)
        leading = story_size * 0.94
        y = 86 + (len(story_lines) - 1) * leading
        c.setFont(story_font, story_size)
        c.setLineJoin(1)
        for ln in story_lines:
            x = (W - c.stringWidth(ln, story_font, story_size)) / 2
            c.setFillColorRGB(*stroke_rgb)
            for ox, oy in ((3.6, -3.6), (2.4, -2.4), (1.2, -1.2)):
                c.drawString(x + ox, y + oy, ln)
            texto = c.beginText(x, y)
            texto.setFont(story_font, story_size)
            texto.setTextRenderMode(2)
            c.setFillColorRGB(*fill_rgb)
            c.setStrokeColorRGB(*stroke_rgb)
            c.setLineWidth(max(2.0, story_size * 0.055))
            texto.textOut(ln)
            c.drawText(texto)
            y -= leading

    brand_badge(y=12)
    c.showPage()
    fit_page()

    # -------------------------------------------- 2) POEMA DE ABERTURA
    # Catalogo com dedicatória própria (P1) substitui o poema genérico do México.
    has_dedication_page = any((p.get("layout") or "") == "dedication" for p in (pages or []))
    if not has_dedication_page:
        bg(CREAM)
        corner_flourish(26, H - 120, 1, 1)
        corner_flourish(W - 26, 120, -1, -1)
        c.setFillColorRGB(*INK)
        c.setFont(F["italic"], 17)
        lines = split_lines(tr["opening"], F["italic"], 17, W * 0.66)
        y = H / 2 + (len(lines) - 1) * 14
        for ln in lines:
            c.drawCentredString(W / 2, y, ln)
            y -= 28
        c.showPage()
        fit_page()

    # ------------------------- 3) FEITO ESPECIALMENTE PARA {NOME}
    if name or portrait:
        bg(CREAM)
        corner_flourish(26, H - 120, 1, 1)
        corner_flourish(W - 26, 120, -1, -1)
        c.setFillColorRGB(*INK)
        c.setFont(F["italic"], 15)
        c.drawCentredString(W / 2, H - 96, _win(tr["made_for"]))
        if name:
            c.setFillColorRGB(*NAVY)
            c.setFont(F["body"], 34)
            c.drawCentredString(W / 2, H - 136, _win(name).upper())

        # retrato circular do protagonista
        pr = reader(portrait)
        if pr:
            R = 108.0
            cx, cy = W / 2, H / 2 + 6
            c.saveState()
            p = c.beginPath()
            p.circle(cx, cy, R)
            c.clipPath(p, stroke=0, fill=0)
            iw, ih = pr.getSize()
            s = max((2 * R) / iw, (2 * R) / ih)
            dw, dh = iw * s, ih * s
            c.drawImage(
                pr, cx - dw / 2, cy - dh / 2, dw, dh, preserveAspectRatio=False, mask="auto"
            )
            c.restoreState()
            c.setStrokeColorRGB(*GOLD)
            c.setLineWidth(4)
            c.circle(cx, cy, R, fill=0, stroke=1)
            star(cx + R * 0.82, cy + R * 0.82, 9, GOLD)

        # personagens extras (pequenos circulos ao redor do protagonista)
        if extra_characters:
            extras = extra_characters[:4]  # no maximo 4 extras
            positions = [
                (W / 2 - 160, H / 2 + 6),
                (W / 2 + 160, H / 2 + 6),
                (W / 2 - 130, H / 2 - 120),
                (W / 2 + 130, H / 2 - 120),
            ]
            for idx, ec in enumerate(extras):
                ec_bytes = ec.get("image_bytes")
                if not ec_bytes:
                    continue
                ec_reader = reader(ec_bytes)
                if not ec_reader or idx >= len(positions):
                    continue
                ecx, ecy = positions[idx]
                eR = 42.0
                c.saveState()
                ep = c.beginPath()
                ep.circle(ecx, ecy, eR)
                c.clipPath(ep, stroke=0, fill=0)
                eiw, eih = ec_reader.getSize()
                es = max((2 * eR) / eiw, (2 * eR) / eih)
                edw, edh = eiw * es, eih * es
                c.drawImage(
                    ec_reader,
                    ecx - edw / 2,
                    ecy - edh / 2,
                    edw,
                    edh,
                    preserveAspectRatio=False,
                    mask="auto",
                )
                c.restoreState()
                c.setStrokeColorRGB(*CORAL)
                c.setLineWidth(2.5)
                c.circle(ecx, ecy, eR, fill=0, stroke=1)

        # bencao
        c.setFillColorRGB(*INK)
        c.setFont(F["italic"], 13.5)
        y = H / 2 - 132
        for ln in split_lines(tr["blessing"], F["italic"], 13.5, W * 0.62):
            c.drawCentredString(W / 2, y, ln)
            y -= 20
        c.showPage()
        fit_page()

    # --------------------------------------- 4) DEDICATORIA DOS PAIS
    if dedication and dedication.strip():
        bg(CREAM)
        c.setStrokeColorRGB(*GOLD)
        c.setLineWidth(2)
        c.roundRect(W * 0.12, H * 0.28, W * 0.76, H * 0.44, 22, fill=0, stroke=1)
        star(W / 2, H * 0.66, 12, GOLD)
        c.setFillColorRGB(*NAVY)
        c.setFont(F["italic"], 17)
        lines = split_lines(dedication.strip(), F["italic"], 17, W * 0.60)
        y = H / 2 + (len(lines) - 1) * 13
        for ln in lines:
            c.drawCentredString(W / 2, y, ln)
            y -= 26
        c.setFillColorRGB(*CORAL)
        c.setFont(F["italic"], 13)
        c.drawCentredString(W / 2, H * 0.32, _win(tr["with_love"]))
        c.showPage()
        fit_page()

    # ------ 5) PAGINAS (arte em sangria + estrofe mesclada, sem numeracao)
    # Se preview_pages estiver definido, limita as paginas da historia
    is_preview = preview_pages is not None and len(pages) > preview_pages
    visible_pages = pages[:preview_pages] if is_preview else pages

    for p in visible_pages:
        layout = (p.get("layout") or "story").strip()
        text = p.get("text", "")
        if layout == "dedication":
            bg(CREAM)
            corner_flourish(26, H - 120, 1, 1)
            corner_flourish(W - 26, 120, -1, -1)
            raw = (text or "").replace("\r\n", "\n").strip()
            poem, sep, prose = raw.partition("\n\n")
            if not sep:
                poem, prose = raw, ""
            poem_lines = split_lines(poem, F["italic"], 17, W * 0.66)
            prose_lines = split_lines(prose, F["italic"], 15, W * 0.68) if prose.strip() else []
            items: list[tuple[str, str, float, float]] = [
                (ln, F["italic"], 17.0, 28.0) for ln in poem_lines
            ]
            if poem_lines and prose_lines:
                items.append(("", F["italic"], 0.0, 12.0))
            items.extend((ln, F["italic"], 15.0, 22.0) for ln in prose_lines)
            total_h = sum(item[3] for item in items) if items else 0.0
            y = H / 2 + total_h / 2
            c.setFillColorRGB(*INK)
            for ln, font, size, leading in items:
                if ln:
                    c.setFont(font, size)
                    c.drawCentredString(W / 2, y - size * 0.75, _win(ln))
                y -= leading
            c.showPage()
            fit_page()
            continue
        bg(CREAM)
        ir = reader(p.get("image"))
        if ir:
            full_bleed(ir)
        if layout == "name":
            name_panel(text)
        else:
            band = (p.get("text_band") or "bottom").strip().lower()
            story_caption(text, "top" if band == "top" else "bottom")
        c.showPage()
        fit_page()

    # Pagina de preview: aviso de que o livro completo esta disponivel
    if is_preview:
        bg(CREAM)
        c.setFillColorRGB(*NAVY)
        c.setFont(F["body"], 22)
        c.drawCentredString(W / 2, H / 2 + 40, _win(tr["preview_title"]))
        c.setFillColorRGB(*INK)
        c.setFont(F["italic"], 15)
        preview_lines = split_lines(
            tr["preview_msg"].format(total=len(pages), shown=preview_pages),
            F["italic"],
            15,
            W * 0.65,
        )
        y = H / 2
        for ln in preview_lines:
            c.drawCentredString(W / 2, y, ln)
            y -= 24
        star(W / 2 - 60, H / 2 - 60, 8, GOLD)
        star(W / 2 + 60, H / 2 - 60, 8, CORAL)
        brand_badge(y=H * 0.28)
        c.showPage()
        fit_page()

    # --------------------- 6) CONTRACAPA: POEMA DE ENCERRAMENTO
    bg(SKY)
    last = reader(pages[-1].get("image")) if pages and pages[-1].get("image") else None
    if last:
        full_bleed(last)
        c.setFillColorRGB(1, 1, 1)
        c.setFillAlpha(0.25)
        c.rect(0, 0, W, H, fill=1, stroke=0)
        c.setFillAlpha(1)
    closing = tr["closing_named"].format(name=_win(name)) if name else tr["closing"]
    poem_panel(closing, H * 0.62)
    brand_badge(y=H * 0.24)
    star(60, H - 70, 10, GOLD)
    star(W - 64, H - 96, 8, CORAL)
    c.showPage()
    fit_page()

    # ----------------------------------------- 7) OBRIGADO / THANK YOU
    bg(CREAM)
    corner_flourish(26, H - 120, 1, 1)
    corner_flourish(W - 26, 120, -1, -1)
    # faixa (ribbon) central estilo referencia
    rw, rh = 300.0, 64.0
    rx, ry = W / 2 - rw / 2, H / 2 - rh / 2
    c.setFillColorRGB(*CORAL)
    # pontas dobradas
    pth = c.beginPath()
    pth.moveTo(rx - 26, ry + rh / 2)
    pth.lineTo(rx + 8, ry + rh)
    pth.lineTo(rx + 8, ry)
    pth.close()
    c.drawPath(pth, fill=1, stroke=0)
    pth = c.beginPath()
    pth.moveTo(rx + rw + 26, ry + rh / 2)
    pth.lineTo(rx + rw - 8, ry + rh)
    pth.lineTo(rx + rw - 8, ry)
    pth.close()
    c.drawPath(pth, fill=1, stroke=0)
    c.roundRect(rx, ry, rw, rh, 10, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont(F["body"], 30)
    c.drawCentredString(W / 2, ry + rh / 2 - 10, _win(tr["thanks"]))
    star(W / 2 - rw / 2 - 52, H / 2 + 46, 9, GOLD)
    star(W / 2 + rw / 2 + 52, H / 2 - 52, 8, GOLD)
    c.setFillColorRGB(*NAVY)
    c.setFont(F["brand"], 12)
    c.drawCentredString(W / 2, 46, "Story R Us")
    c.showPage()

    c.save()
    return buf.getvalue()
