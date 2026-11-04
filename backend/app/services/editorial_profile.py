"""Versioned, server-owned editorial inputs for the existing Studio preview."""

import hashlib
import json
import re
from pathlib import Path

ASSET_ROOT = Path(__file__).resolve().parents[1] / "assets/editorial"
CURRENT_VERSION = "2026-11-04.3"
PROFILE_ROOTS = {
    version: ASSET_ROOT / version for version in ("2026-11-04.1", "2026-11-04.2", CURRENT_VERSION)
}
ROLES = ("01_CAPA", "02_LIVRO_ABERTO", "03_LEITURA")


def _root(version: str | None = None) -> Path:
    version = version or CURRENT_VERSION
    try:
        return PROFILE_ROOTS[version]
    except KeyError as exc:
        raise ValueError(f"Versão editorial não suportada: {version}") from exc


def snapshot(version: str | None = None):
    version = version or CURRENT_VERSION
    root = _root(version)
    files = sorted(p for p in root.rglob("*") if p.is_file())
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return {"version": version, "sha256": digest.hexdigest()}


def references(style, version: str | None = None, *, art_only: bool = False):
    root = _root(version)
    config = json.loads((root / "config/storyrus-profile.json").read_text(encoding="utf-8"))
    mode = "cartoon_premium" if style == "cartoon" else "realista_premium"
    paths = config["style"]["modes"][mode]["finish_references"]
    if not art_only:
        paths += [item["path"] for item in config["style"]["common_references"]]
    return [(path, (root / path).read_bytes()) for path in paths]


def uses_backend_typography(profile, role):
    return profile.get("editorial", {}).get("version") == CURRENT_VERSION and role in {
        "01_CAPA",
        "02_LIVRO_ABERTO",
    }


def _remove_section(prompt: str, start: str, end: str | None) -> str:
    boundary = rf"(?=^{re.escape(end)}\n)" if end else r"\Z"
    return re.sub(rf"(?ms)^{re.escape(start)}\n.*?{boundary}", "", prompt)


def _art_master_prompt(master: str) -> str:
    """Keep only shared visual rules; a generation must see exactly one scene."""
    for start, end in (
        ("OBJETIVO E ESCOPO", "FONTES DE REFERÊNCIA"),
        ("TIPOGRAFIA FIXADA", "TÍTULOS E TEXTOS"),
        ("TÍTULOS E TEXTOS", "CAPA"),
        ("CAPA", "CONTINUIDADE E VALIDAÇÃO"),
        ("CONTINUIDADE E VALIDAÇÃO", "ENTREGA"),
        ("ENTREGA", None),
    ):
        master = _remove_section(master, start, end)
    master = re.sub(r"(?m)^Na LEITURA,.*(?:\n|$)", "", master)
    master = re.sub(
        r"(?m)^\s*[23]\. (?:texto-meu-pai-meu-heroi|titulo-amor-de-bisavo)\.png.*(?:\n|$)",
        "",
        master,
    )
    return master


def prompt(project, language, role, *, include_text: bool = True):
    profile = project.book_profile
    editorial = profile["editorial"]
    version = editorial.get("version")
    root = _root(version)
    if editorial != snapshot(version):
        raise ValueError("Perfil editorial deste trabalho indisponível; preserve a versão original")
    master = (root / "prompts/PROMPT_MESTRE.txt").read_text(encoding="utf-8")
    scene = (root / f"prompts/{role}.txt").read_text(encoding="utf-8")
    texts = profile["locales"][language]
    if not include_text:
        master = _art_master_prompt(master)
        art_path = root / f"prompts/{role}_ARTE.txt"
        scene = (art_path if art_path.is_file() else root / f"prompts/{role}.txt").read_text(
            encoding="utf-8"
        )
        texts = {}
    data = {
        "language": "en-US" if language == "en" else language,
        "texts": texts,
        "name": project.child_name,
        "age": project.child_age,
        "theme": profile.get("theme_description") or project.theme,
        "characters": profile.get("characters"),
        "continuity": {k: profile.get(k) for k in ("visual_identity", "costume", "palette")},
        "style": project.style,
        "style_reference_roles": [
            p for p, _ in references(project.style, version, art_only=not include_text)
        ],
    }
    return master + "\n" + scene + "\nDADOS DO LIVRO:\n" + json.dumps(data, ensure_ascii=False)
