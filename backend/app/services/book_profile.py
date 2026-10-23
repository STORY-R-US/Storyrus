"""Story R Us creation contract. Prompts stay server-side; state survives reloads."""

from __future__ import annotations

import re
import unicodedata

from fastapi import HTTPException

VERSION = 1
LANGUAGES = {"pt-BR": "PORTUGUES", "en": "INGLES", "es": "ESPANHOL"}
TYPOGRAPHY = (
    "Tipografia unica em toda a serie: rounded sans-serif Nunito, Medium/SemiBold, "
    "Bold no titulo, cor #172A3A. Sem cursiva, manuscrita, serifada ou Comic Sans."
)
IDENTITY = (
    "IDENTIDADE: fotografias ORIGINAIS vencem a ficha visual, que vence a capa aprovada; "
    "geracoes anteriores servem apenas para continuidade. Preserve formato do rosto, "
    "olhos e sua cor e tamanho natural, sobrancelhas, nariz, boca, sorriso, bochechas, "
    "cabelo, textura, comprimento, linha do cabelo, pele, etnia, idade e proporcoes. "
    "Sem crianca generica, embelezar, envelhecer, rejuvenescer ou aumentar olhos/cabeca. "
    "Animais reais: mesma raca, porte, cor, pelagem, manchas, focinho, olhos e orelhas. "
    "Animais inventados: mesma aparencia definida na ficha visual em todas as cenas. "
    "Antes de gerar confira rosto, olhos, cabelo, idade, pele, animal, titulo, "
    "tipografia, figurino e paleta. Anatomia natural, sem dedos/bracos extras. "
    "Sem marca d'agua, collage, painel ou grade."
)


def enabled(project) -> bool:
    return bool((project.book_profile or {}).get("version") == VERSION)


def update(project, **values) -> dict:
    profile = {**(project.book_profile or {}), **values}
    project.book_profile = profile
    return profile


_TITLE_LINE = re.compile(r"(?im)^(?:t[íi]tulo|title)\s*:[^\n]*")


def retitle(text: str, title: str) -> str:
    """Troca só a linha de título e conserva o restante da história."""
    line = f"Título: {title}"
    body = text.strip()
    if not body:
        return line
    if _TITLE_LINE.match(body):
        return _TITLE_LINE.sub(line, text, count=1)
    return f"{line}\n\n{body}"


def apply_title(project, title: str) -> None:
    """Grava o título na ficha, nos idiomas e na história, sem voltar a etapa."""
    from app.services import purchase_flow

    title = title.strip()
    profile = project.book_profile or {}
    locales = {
        lang: {**locale, "title": title} if isinstance(locale, dict) else locale
        for lang, locale in (profile.get("locales") or {}).items()
    }
    stories = {
        lang: retitle(text, title) if isinstance(text, str) else text
        for lang, text in (profile.get("stories") or {}).items()
    }
    update(project, title=title, locales=locales, stories=stories)
    if isinstance(project.story_text, str) and project.story_text.strip():
        project.story_text = retitle(project.story_text, title)
    purchase_flow.update(project, title=title)


def require_stage(project, *stages: str) -> None:
    if enabled(project) and (project.book_profile or {}).get("stage") not in stages:
        raise HTTPException(409, "Conclua e aprove a etapa atual antes de continuar")


def initial_profile(body) -> dict:
    languages = [
        lang for lang in LANGUAGES if lang in (body.languages or [body.language or "pt-BR"])
    ]
    if (body.language or "pt-BR") not in languages:
        raise HTTPException(400, "Inclua o idioma principal nos idiomas do livro")
    return {
        "version": VERSION,
        "stage": "ficha",
        "title": (body.title or "").strip(),
        "gender": body.gender,
        "languages": languages,
        "current_page": 0,
        "theme_description": (body.theme_description or body.theme or "").strip(),
        "characters": (body.characters or "").strip(),
    }


def validate_ficha(project, photos: list) -> None:
    profile = project.book_profile or {}
    missing = []
    for label, value in (
        ("nome", (project.child_name or "").strip()),
        ("idade", project.child_age is not None),
        ("genero", profile.get("gender")),
        ("tema", project.theme),
        ("estilo", project.style in {"realistic", "cartoon"}),
        ("capa", project.cover_type in {"hard", "soft"}),
        ("tamanho", project.book_size in {"M", "P"}),
        ("idioma", profile.get("languages")),
        ("foto", photos),
    ):
        if not value:
            missing.append(label)
    if missing:
        raise HTTPException(400, "Complete a ficha: " + ", ".join(missing))
    for extra in project.extra_characters or []:
        if not extra.get("storage_key"):
            raise HTTPException(
                400, f"Envie a foto de {extra.get('name') or 'cada personagem extra'}"
            )


def filename(language: str, kind: str, title: str) -> str:
    slug = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", slug).strip("_")[:120] or "Livro"
    return f"{LANGUAGES[language]}_{kind}_{slug}.png"


def art_direction(style: str | None) -> str:
    if style == "cartoon":
        return (
            "Cartoon premium: ilustracao claramente DESENHADA, linhas suaves, volumes "
            "arredondados, cores alegres e sofisticadas, acabamento digital editorial. "
            "Mais desenho que o realista; rosto reconhecivel derivado da foto, olhos naturais."
        )
    return (
        "Realista premium: fotografia editorial infantil, pele e cabelo naturais, luz suave, "
        "profundidade fotografica, composicao comercial elegante. Sem plastico, CGI ou filtro."
    )


def format_directive(project, *, physical: bool = False) -> str:
    cm = 15 if project.book_size == "P" else 20
    if physical:
        return (
            f"Livro fisico {cm}x{cm} cm, paginas quadradas iguais, cantos suavemente "
            f"arredondados, capa {'dura' if project.cover_type == 'hard' else 'flexivel'}."
        )
    return (
        f"FORMATO: quadrado {cm}x{cm} cm, corte reto, arte ate a borda, "
        "sangria 5 mm para fora; rosto, maos e texto a 5 mm para dentro do corte e da dobra. "
        "Sem cantos arredondados na arte impressa."
    )


def continuity(project) -> str:
    p = project.book_profile or {}
    return (
        f"Ficha visual: {p.get('visual_identity', '')}. Figurino TRAVADO: {p.get('costume', '')}. "
        f"Paleta TRAVADA: {p.get('palette', '')}. Animal: {p.get('animal', '')}. "
        + IDENTITY
        + " "
        + TYPOGRAPHY
    )


def preview_prompt(project, language: str, kind: str) -> str:
    p = project.book_profile
    locale = p["locales"][language]
    title = locale["title"]
    common = (
        continuity(project)
        + " "
        + art_direction(project.style)
        + " "
        + format_directive(project, physical=True)
    )
    if kind == "01_CAPA":
        return (
            "CAPA quadrada, fotografia real em sangria total, corte reto. "
            f"{project.child_name} em destaque, a mesma pessoa da foto, com a roupa da fotografia. "
            f"Cenario do tema {p.get('theme_description') or project.theme}. "
            "Ceu limpo no terco de cima, sem rosto e sem objeto, porque o titulo entra ali depois. "
            "Sem letras, sem logo, sem moldura e sem faixa. "
            + format_directive(project)
            + " "
            + continuity(project)
        )
    if kind == "02_LIVRO_ABERTO":
        return (
            "LIVRO FISICO ABERTO em proporcao total 2:1. Duas paginas QUADRADAS "
            "iguais lado a lado, dobra central natural, sem esticar/comprimir o conteudo. "
            "Livro ocupa o quadro. Cada lado tem ilustracao da MESMA crianca e 2 a 5 "
            "linhas de texto, margens amplas, longe da dobra/rostos. "
            f"Esquerda: «{locale['left']}». Direita: «{locale['right']}». " + common
        )
    return (
        f"A CRIANCA DA FOTO ORIGINAL, {project.child_name}, segura ou le seu proprio livro "
        "em ambiente acolhedor, com alegria e carinho. A referencia de CAPA deve ser "
        "impressa IDENTICA no livro fisico, nunca reinventada. "
        f"Titulo exato «{title}», livro quadrado claramente visivel. Enquadramento 1:1. " + common
    )


def back_cover_prompt(project, language: str) -> str:
    p = project.book_profile or {}
    return (
        "CONTRACAPA quadrada, fotografia real em sangria total, corte reto. "
        f"As mesmas pessoas da capa, {project.child_name}, vistas de costas, olhando a paisagem. "
        "Roupa da fotografia original. Ceu limpo no terco de cima, sem rosto, sem objeto, "
        f"sem letras, sem logo e sem QR. Idioma {language}; a marca entra depois. "
        f"Tema: {p.get('theme_description') or project.theme}. "
        + format_directive(project)
        + " "
        + continuity(project)
    )


def avatar_prompt(project) -> str:
    return (
        f"Retrato-base de {project.child_name}, {project.child_age} anos. Desenhe ESTA "
        "crianca da foto, reconhecivel na hora. Rosto com qualidade de camera; no realista, "
        "corpo ilustrado; no cartoon, corpo desenhado e rosto ainda derivado da foto. "
        "Meio corpo, cabeca natural, sem aumentar olhos. Fundo creme, sem texto, sem moldura. "
        "Nao copie a roupa da foto. Trave rosto, cabelo, franja, testa, pele e idade. "
        "Proibido embelezar, envelhecer, chibi ou crianca generica. " + IDENTITY
    )
