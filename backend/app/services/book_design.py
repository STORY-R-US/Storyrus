"""One frozen, complete catalog design shared by every stage of a book."""

import hashlib
import json
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException

from app.services import book_profile, visual_reference

ROOT = Path(__file__).resolve().parents[1] / "assets/composition_examples"


def _signature(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


@lru_cache(maxsize=1)
def definitions():
    return json.loads((ROOT / "book-designs-v1.json").read_text(encoding="utf-8"))


def reference(design, stage):
    role = stage if stage in {"cover", "holding"} else "page"
    family = design["reference_set"]
    suffix = "png" if family == "adventure" else "jpg"
    return (ROOT / "catalog" / f"{family}-{role}.{suffix}").read_bytes()


def snapshot(model_id):
    data = definitions()
    if model_id not in data["models"]:
        raise HTTPException(400, "Escolha um padrão do Catálogo disponível")
    model = json.loads(json.dumps(data["models"][model_id]))
    model.update(id=model_id, version=data["version"])
    model["reference_sha256"] = {
        role: hashlib.sha256(reference(model, role)).hexdigest()
        for role in ("cover", "page", "holding")
    }
    return {**model, "sha256": _signature(model)}


def resolve(profile):
    stored = profile.get("book_design")
    if not stored:
        return None
    if stored != snapshot(stored.get("id")):
        raise HTTPException(
            409, "O padrão visual deste livro foi alterado; escolha novamente antes de gerar"
        )
    return stored


def select(project, requested):
    previous = resolve(project.book_profile or {})
    if requested == "auto" and previous and previous["style"] == project.style:
        return previous
    if requested == "auto":
        family = visual_reference.catalog_family(project.style, project.theme or "")
        requested = "family" if family in {"family", "creative"} else family
    design = snapshot(requested)
    if design["style"] != project.style:
        raise HTTPException(400, "Escolha um padrão do Catálogo compatível com o estilo do livro")
    if previous != design:
        # Changing the design invalidates the old cover decision, not the user's text.
        book_profile.update(
            project, book_design=design, cover_calibration=None, visual_master_preset=None
        )
    return design


def apply_policy(design, policy):
    cover, interior = design["cover"], design["interior"]
    policy["visual"]["artDirection"] = design["finish"]
    policy["typography"].update(
        coverPlacement=cover["placement"],
        coverAlignment=cover["alignment"],
        titleWidthRatio=cover["font_ratio"],
        longTitleWidthRatio=cover["long_font_ratio"],
        bodyAlignment=interior["alignment"],
        bodyWidthRatio=interior["font_ratio"],
    )
    policy["referenceComposition"].update(
        coverRegion=cover["region"], bodyRegion=interior["region"]
    )
    return policy


def preview_interior(design):
    """Preview both story moments without changing existing paid-page contracts."""
    interior = design["interior"]
    if design["id"] == "family":
        return {
            **interior,
            "mode": "two_scenes",
            "region": [0.08, 0.055, 0.92, 0.33],
            "description": "Two facing illustrated pages. Each page has its own sequential story passage in quiet upper scenery and a distinct meaningful action with the project's characters below. No text over characters and neither page is illustration-only or text-only.",
        }
    return interior


def prompt(design, role, action, *, text_region=None):
    interior = design["interior"]
    if role in {"open_book", "preview_page"}:
        interior = preview_interior(design)
    cover_direction = ""
    if design["id"] == "family" and role == "cover":
        cover_direction = (
            "AMOR DE BISAVÓ COVER COMPOSITION: compose the title as an integral part of "
            "the finished cover image, in the upper-right natural scenery, with harmonious "
            "color, contrast and generous breathing room. The server adds the exact approved "
            "title after illustration; do not draw lettering in this art stage. Reserve the "
            "entire measured text_region plus a clear margin as quiet continuous scenery. "
            "Keep EVERY character completely outside this title area, including hair, face, "
            "body, clothing, arms and hands. Reframe or reposition the characters naturally "
            "on the left and below the title area rather than placing text over them. "
            "Continue the same illustrated background behind the title: no separate label, "
            "panel, banner, box or blank strip. "
        )
    layout = (
        {"cover": design["cover"]}
        if role == "cover"
        else {"holding": design["holding"]}
        if role == "holding"
        else {"interior": interior}
        if role != "back_cover"
        else {}
    )
    return (
        "COMPLETE CATALOG BOOK DESIGN — authoritative for the whole book. "
        "Use this one design for cover, typography, interior, binding and held-book presentation. "
        "Do not combine layouts or finishes from unrelated examples. Original project photos alone "
        "define the cast and identity. The catalog book defines structure, not its names, words or props. "
        "Any approved project cover defines wardrobe, palette and setting for all following pages. "
        "Generate ONLY the requested role, never combine cover and interior in one image. "
        "The actual requested theme and action alone define story objects and setting. "
        "Never import people, scenery or story props from catalog examples. "
        + (
            "COVER ONLY: ONE single square front-cover face, not an open book, spread, "
            "front-and-back pair, diptych, gutter, central fold or two facing pages. "
            if role == "cover"
            else ""
        )
        + cover_direction
        + json.dumps(
            {
                "design_id": design["id"],
                "design_sha256": design["sha256"],
                "role": role,
                **layout,
                "finish": design["finish"],
                "text_region": text_region,
                "current_action": action,
            },
            ensure_ascii=False,
        )
    )


def pair_content(design, number, passages):
    """Keep every literal passage once across a two-page catalog spread."""
    mode = design["interior"]["mode"]
    if mode == "two_scenes":
        return "scene", passages[number - 1], [number]
    first = ((number - 1) // 2) * 2
    text_page = first + (1 if mode == "text_left" else 2)
    return (
        ("reading", "\n\n".join(passages[first : first + 2]), [first + 1, first + 2])
        if number == text_page
        else ("illustration", "", [first + 1, first + 2])
    )
