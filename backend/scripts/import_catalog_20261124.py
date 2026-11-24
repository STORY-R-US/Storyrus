"""Rebuild the approved 2026-11-24 catalog batch without changing frozen v4 books.

Usage from the repository root:
    python backend/scripts/import_catalog_20261124.py --manifest /path/catalog_import.json
    python backend/scripts/import_catalog_20261124.py --manifest /path/catalog_import.json \
        --check --verify-assets

The input is the approved import manifest (six updates and fifty new previews),
not a live API payload. This script changes only the v5 design registry and its
web mirror. Image export, publication, customer projects and payments are separate.
"""

import argparse
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "backend/app/assets/composition_examples"
WEB_REGISTRY = ROOT / "apps/web/src/catalogModels.json"
BATCH = "20261124"
VERSION = 5
PREVIOUS_VERSION = 4
BASE_MAX_INDEX = 68
ROLES = ("cover", "page", "holding")
LANGUAGES = {"pt": "pt-BR", "en": "en", "es": "es"}
IMPORT_ROLES = {"cover": "cover", "page": "open_book", "holding": "reading"}

FINISH = (
    "MEU PAI, MEU HEROI TYPOGRAPHY AND PHOTOGRAPHIC STANDARD, approved 2026-11-24: "
    "natural refined photographic editorial realism throughout the cover, interior and "
    "reading portrait. Lifelike recognizable faces at their real ages, delicate natural "
    "skin texture, individual irregular hair strands, proportional non-glassy eyes, "
    "spontaneous expressions, plausible hands and anatomy. Real environmental light "
    "appropriate to the story's time and place, gentle contact shadows, natural optical "
    "depth and tactile materials. Heavy rounded solid navy cover title with restrained "
    "small golden ornaments; compact rounded navy Medium narrative, never headline-sized. "
    "No painted or illustrated people/scenery, plastic CGI, HDR, skin smoothing, oversized "
    "eyes or invented cast. Original project photos alone define identity; the selected "
    "catalog supplies composition and finish, not its sample people, names or objects. "
    "The user may change the story theme: adapt actions and setting to that theme. "
    "The three languages preserve the approved scene and identity while changing text."
)
SCENE_DIRECTION = (
    "Follow this selected photographic cover's composition, subject scale and rounded "
    "navy title hierarchy. Preserve complete faces, hair, hands and meaningful activity "
    "outside the measured title reserve, using a continuous natural setting. Adapt the "
    "setting and props to the actual project theme; never import sample identities. "
    "No portrait inset, collage, stretched edges, mirrored fill or artificial blank band. "
    "At the art stage do not draw sample lettering, titles or ornaments; the server "
    "composes the literal approved title and restrained gold accents afterward."
)
INTERIOR_DESCRIPTION = (
    "Two equally sized square 20 x 20 cm pages form a physical open spread of 2:1. "
    "Each printed page contains a distinct natural photographic story moment with "
    "the approved cast, ages and wardrobe. Compact rounded Medium navy narrative sits "
    "in quiet upper scenery with comfortable outer and gutter margins; preserve "
    "faces, hands and actions. Prefer two short lines, at most four, with photographs "
    "occupying about 75-80 percent of useful page area. Never an illustration-only "
    "or text-only page, duplicated passage or illustrated photographic substitute."
)
HOLDING_POSE = (
    "A candid photographic reading moment with only the project's authorized cast, "
    "at their correct ages. The appropriate reader naturally supports the complete "
    "square 20 x 20 cm hardback below the face; preserve hands, realistic binding, "
    "paper block and contact shadows. The exact approved cover and literal title "
    "appear on one front board, with a separate plain complementary blue rear board. "
    "Use an adult reader for a newborn, with the infant's head and neck fully supported; "
    "never make a newborn hold a book. Adult couple stories retain their adult cast. "
    "Do not copy the example reader's identity or redraw a different cover."
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def example_names(entry):
    """Keep a couple/sibling name phrase intact; never rename an incidental adult."""
    cast = entry["approved_editorial"]["protagonists"]
    require(bool(cast), "New books require an approved demonstration protagonist")
    pair = [
        person["name"]
        for person in cast
        if "do casal" in person["role"]
        or person["role"] in {"irmão protagonista", "irmã protagonista"}
    ]
    names = pair if len(pair) > 1 else [cast[0]["name"]]
    return {
        language: conjunction.join(names)
        for language, conjunction in {"pt-BR": " e ", "en": " and ", "es": " y "}.items()
    }


def approved_design(template, entry, index, *, new):
    design = copy.deepcopy(template)
    design.update(
        name=entry["titles"]["pt"],
        style="realistic",
        catalog_index=index,
        reference_set="catalog",
        title_templates={target: entry["titles"][source] for source, target in LANGUAGES.items()},
        finish=FINISH,
        sources={role: f"catalog_models/realistic-{index}-{role}-{BATCH}.webp" for role in ROLES},
        visual={
            "finish": "premium_photographic_editorial_realism",
            "lighting": "natural_environmental_light_appropriate_to_story_time_and_place",
            "background": "continuous_detailed_narrative_setting_no_stretched_mirrored_or_blurred_edge_fills",
            "color": "theme_appropriate_balanced_color_and_natural_skin",
        },
    )
    design["reference_files"] = dict(design["sources"])
    design["cover"]["scene_direction"] = SCENE_DIRECTION
    design["interior"].update(
        mode="two_scenes", alignment="center", font_ratio=0.038, description=INTERIOR_DESCRIPTION
    )
    design.pop("preview_interior", None)
    design["typography"].update(
        titleFontFile="Nunito-Black.ttf",
        bodyFontFile="Nunito-Medium.ttf",
        titleWeight=900,
        baseWeight=500,
        titleColor="#061A45",
        color="#071337",
        titleLineHeight=1.05,
        lineHeight=1.2,
        titleBalancedLines=3,
        titleGoldOrnaments=True,
        longTitleMinCharacters=42,
    )
    design["holding"]["pose"] = HOLDING_POSE
    if new:
        design["stable_slug"] = entry["stable_slug"]
        names = example_names(entry)
        design["example_name"] = names["pt-BR"]
        design.pop("example_names", None)
        if len(set(names.values())) > 1:
            design["example_names"] = names
    return design


def build_registries(payload, baseline, web):
    require(payload.get("publication_authorization_received") is True, "Import is not approved")
    require(baseline["version"] == PREVIOUS_VERSION, "Expected the frozen v4 registry")
    maximum = max(model["catalog_index"] for model in baseline["models"].values())
    require(maximum == BASE_MAX_INDEX, f"Unexpected baseline maximum: {maximum}")
    updates = payload["updates"]
    inserts = sorted(payload["inserts"], key=lambda entry: entry["production_order"])
    require(len(updates) == 6, "Expected exactly six realistic preview updates")
    require(
        {entry["existing_catalog_index"] for entry in updates} == set(range(62, 68)),
        "The approved updates are limited to indices 62-67",
    )
    require(
        [entry["production_order"] for entry in inserts] == list(range(1, 51)),
        "Expected fifty unique production orders, 1-50",
    )
    require(len({entry["stable_slug"] for entry in inserts}) == 50, "Duplicate stable slug")
    result = copy.deepcopy(baseline)
    result["version"] = VERSION
    mirrored = copy.deepcopy(web)
    touched = []
    for new, entries in ((False, updates), (True, inserts)):
        for entry in entries:
            require(
                entry["visual_style"]["observed_key"] == "realistic",
                "Only realistic assets supplied",
            )
            index = maximum + entry["production_order"] if new else entry["existing_catalog_index"]
            key = f"catalog-realistic-{index}"
            require(set(entry["titles"]) == set(LANGUAGES), f"Missing title locale: {key}")
            for language in LANGUAGES:
                assets = entry["localized_preview_assets"][language]
                require(
                    set(assets) == set(IMPORT_ROLES.values()),
                    f"Missing preview role: {key}/{language}",
                )
            if new:
                require(
                    index not in {m["catalog_index"] for m in baseline["models"].values()},
                    "ID collision",
                )
                require(
                    not any(
                        model.get("stable_slug") == entry["stable_slug"] and old_key != key
                        for old_key, model in mirrored.items()
                    ),
                    f"Stable slug already assigned to another ID: {entry['stable_slug']}",
                )
                require(
                    key not in mirrored or mirrored[key].get("stable_slug") == entry["stable_slug"],
                    f"Catalog ID already belongs to another book: {key}",
                )
                template = baseline["models"]["catalog-realistic-21"]
            else:
                template = baseline["models"][key]
                require(
                    template["title_templates"]["pt-BR"] == entry["expected_existing_title_pt"],
                    f"Unexpected old title: {key}",
                )
                require(
                    key in mirrored and mirrored[key]["style"] == "realistic",
                    f"Missing web model: {key}",
                )
            model = approved_design(template, entry, index, new=new)
            result["models"][key] = model
            mirror = {
                **mirrored.get(key, {}),
                "id": key,
                "catalog_index": index,
                "style": "realistic",
                "available": True,
                "reason": None,
                "titles": dict(entry["titles"]),
                "example_name": model["example_name"],
                "sources": dict(model["sources"]),
            }
            if "example_names" in model:
                mirror["example_names"] = {
                    source: model["example_names"][target] for source, target in LANGUAGES.items()
                }
            if new:
                mirror["stable_slug"] = entry["stable_slug"]
            mirrored[key] = mirror
            touched.append(index)
    new_keys = {f"catalog-realistic-{index}" for index in range(69, 119)}
    require(
        set(mirrored) == set(web) | new_keys,
        "Unexpected web model removal",
    )
    return result, mirrored, touched


def verify_assets(designs, touched):
    from PIL import Image

    public = ROOT / "apps/web/public/exemplos"
    for index in touched:
        design = designs["models"][f"catalog-realistic-{index}"]
        for role in ROLES:
            reference = ASSETS / design["reference_files"][role]
            for language in LANGUAGES:
                source = public / f"catalog-{BATCH}/{index}/{role}-{language}.webp"
                with Image.open(source) as image:
                    require(image.format == "WEBP", f"Invalid exported image: {source}")
                    image.verify()
                if language == "pt":
                    require(
                        reference.read_bytes() == source.read_bytes(),
                        f"Backend/web reference mismatch: {index}/{role}",
                    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument(
        "--check", action="store_true", help="Check reproducibility without writing"
    )
    parser.add_argument(
        "--verify-assets",
        action="store_true",
        help="Verify all 504 web images and 168 backend copies",
    )
    args = parser.parse_args()
    baseline = read_json(ASSETS / f"book-designs-v{PREVIOUS_VERSION}.json")
    designs, web, touched = build_registries(
        read_json(args.manifest), baseline, read_json(WEB_REGISTRY)
    )
    target = ASSETS / f"book-designs-v{VERSION}.json"
    if target.exists():
        old = read_json(target)
        unaffected = set(baseline["models"]) - {f"catalog-realistic-{i}" for i in range(62, 68)}
        require(set(old["models"]) == set(designs["models"]), "Existing v5 has unrelated additions")
        require(
            all(old["models"][key] == baseline["models"][key] for key in unaffected),
            "Existing v5 contains unrelated changes",
        )
    if args.verify_assets:
        verify_assets(designs, touched)
    for path, data in ((target, designs), (WEB_REGISTRY, web)):
        if args.check:
            require(
                path.is_file() and read_json(path) == data, f"Registry is not reproducible: {path}"
            )
        else:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "version": VERSION,
                "updated": list(range(62, 68)),
                "inserted": list(range(69, 119)),
                "assets_verified": args.verify_assets,
                "check_only": args.check,
            }
        )
    )


if __name__ == "__main__":
    main()
