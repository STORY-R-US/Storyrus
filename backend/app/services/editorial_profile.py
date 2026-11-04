"""Versioned, server-owned editorial inputs for the existing Studio preview."""

import hashlib
import json
import re
from pathlib import Path

ASSET_ROOT = Path(__file__).resolve().parents[1] / "assets/editorial"
CURRENT_VERSION = "2026-11-04.2"
PROFILE_ROOTS = {version: ASSET_ROOT / version for version in ("2026-11-04.1", CURRENT_VERSION)}
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


def references(style, version: str | None = None):
    root = _root(version)
    config = json.loads((root / "config/storyrus-profile.json").read_text(encoding="utf-8"))
    mode = "cartoon_premium" if style == "cartoon" else "realista_premium"
    paths = config["style"]["modes"][mode]["finish_references"]
    paths += [item["path"] for item in config["style"]["common_references"]]
    return [(path, (root / path).read_bytes()) for path in paths]


def uses_backend_typography(profile, role):
    return profile.get("editorial", {}).get("version") == CURRENT_VERSION and role in {
        "01_CAPA",
        "02_LIVRO_ABERTO",
    }


def _remove_section(prompt: str, start: str, end: str) -> str:
    return re.sub(rf"(?ms)^{re.escape(start)}\n.*?(?=^{re.escape(end)}\n)", "", prompt)


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
    if uses_backend_typography(profile, role) and not include_text:
        master = _remove_section(master, "TIPOGRAFIA FIXADA", "TÍTULOS E TEXTOS")
        master = _remove_section(master, "TÍTULOS E TEXTOS", "CAPA")
        master = _remove_section(
            master,
            "CAPA" if role == "01_CAPA" else "LIVRO ABERTO",
            "LIVRO ABERTO" if role == "01_CAPA" else "LEITURA",
        )
        master = _remove_section(master, "CONTINUIDADE E VALIDAÇÃO", "ENTREGA")
        scene = (root / f"prompts/{role}_ARTE.txt").read_text(encoding="utf-8")
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
        "style_reference_roles": [p for p, _ in references(project.style, version)],
    }
    return master + "\n" + scene + "\nDADOS DO LIVRO:\n" + json.dumps(data, ensure_ascii=False)
