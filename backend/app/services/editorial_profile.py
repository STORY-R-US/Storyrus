"""Versioned, server-owned editorial inputs for the existing Studio preview."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "assets/editorial/2026-11-04.1"
ROLES = ("01_CAPA", "02_LIVRO_ABERTO", "03_LEITURA")


def snapshot():
    files = sorted(p for p in ROOT.rglob("*") if p.is_file())
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(path.read_bytes())
    return {"version": "2026-11-04.1", "sha256": digest.hexdigest()}


def references(style):
    config = json.loads((ROOT / "config/storyrus-profile.json").read_text(encoding="utf-8"))
    mode = "cartoon_premium" if style == "cartoon" else "realista_premium"
    paths = config["style"]["modes"][mode]["finish_references"]
    paths += [item["path"] for item in config["style"]["common_references"]]
    return [(path, (ROOT / path).read_bytes()) for path in paths]


def prompt(project, language, role):
    profile = project.book_profile
    if profile["editorial"] != snapshot():
        raise ValueError("Perfil editorial deste trabalho indisponível; preserve a versão original")
    master = (ROOT / "prompts/PROMPT_MESTRE.txt").read_text(encoding="utf-8")
    scene = (ROOT / f"prompts/{role}.txt").read_text(encoding="utf-8")
    data = {
        "language": "en-US" if language == "en" else language,
        "texts": profile["locales"][language],
        "name": project.child_name,
        "age": project.child_age,
        "theme": profile.get("theme_description") or project.theme,
        "characters": profile.get("characters"),
        "continuity": {k: profile.get(k) for k in ("visual_identity", "costume", "palette")},
        "style": project.style,
        "style_reference_roles": [p for p, _ in references(project.style)],
    }
    return master + "\n" + scene + "\nDADOS DO LIVRO:\n" + json.dumps(data, ensure_ascii=False)
