"""Add the fifty reviewed Cartoon editions without modifying frozen v1-v5 projects."""

import argparse
import copy
import json
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "backend/app/assets/composition_examples"
PUBLIC = ROOT / "apps/web/public/exemplos"
WEB = ROOT / "apps/web/src"
ROLES = ("cover", "page", "holding")
LANGUAGES = ("pt", "en", "es")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def build():
    previous = read(ASSETS / "book-designs-v5.json")
    result = copy.deepcopy(previous)
    result["version"] = 6
    web = read(WEB / "catalogModels.json")
    localized = read(WEB / "localizedExamples.json")
    style = previous["models"]["catalog-cartoon-8"]
    for index in range(69, 119):
        key = f"catalog-cartoon-{index}"
        realistic_key = f"catalog-realistic-{index}"
        model = copy.deepcopy(previous["models"][realistic_key])
        model["style"] = "cartoon"
        model["stable_slug"] += "-cartoon"
        model["finish"] = style["finish"] + (
            " AMOR DE BISAVO is the shared Cartoon character and rendering standard. "
            "Keep the approved cast, ages, wardrobe and story moments identical in PT, EN and ES. "
            "Only the printing inside the held book is Cartoon; readers and room remain photographic."
        )
        model["visual"] = copy.deepcopy(style["visual"])
        model["visual"]["finish"] = "amor_de_bisavo_cartoon"
        model["cover"]["scene_direction"] = (
            "Follow this exact Cartoon cover composition and the Amor de Bisavo rendering style. "
            "Preserve recognizable project faces, correct ages, clothing and scene actions. "
            "Keep faces, hair and hands clear of the upper title reserve. Use continuous detailed "
            "scenery, square full-bleed hardback format and a slim left spine, without collage, "
            "stretched edges or artificial bands. Do not import sample people or names. "
            "The server composes the literal rounded navy title and restrained gold accents."
        )
        model["interior"]["description"] = (
            "Two equally sized square 20 x 20 cm pages form a physical 2:1 open spread. "
            "Each page contains its own approved story moment in the Amor de Bisavo Cartoon style. "
            "Preserve the cover cast, faces, ages and wardrobe. Compact rounded navy narrative "
            "sits in quiet upper scenery with outer and gutter margins, clear of faces and hands. "
            "Keep exactly the same scenes across PT, EN and ES, changing only the words."
        )
        model["sources"] = {
            role: f"catalog_models/cartoon-{index}-{role}-20261124.webp" for role in ROLES
        }
        model["reference_files"] = dict(model["sources"])
        result["models"][key] = model
        web[key] = {
            **copy.deepcopy(web[realistic_key]),
            "id": key,
            "style": "cartoon",
            "stable_slug": model["stable_slug"],
            "sources": dict(model["sources"]),
        }
        for role in ROLES:
            paths = {lang: f"cartoon-20261124/{index}/{role}-{lang}.webp" for lang in LANGUAGES}
            localized[model["sources"][role]] = paths
            localized[paths["pt"]] = paths
    return result, web, localized


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    designs, web, localized = build()
    for index in range(69, 119):
        for role in ROLES:
            pt = PUBLIC / f"cartoon-20261124/{index}/{role}-pt.webp"
            reference = ASSETS / designs["models"][f"catalog-cartoon-{index}"]["sources"][role]
            for lang in LANGUAGES:
                path = PUBLIC / f"cartoon-20261124/{index}/{role}-{lang}.webp"
                with Image.open(path) as image:
                    # Some approved spreads include the surrounding scene in a square photo.
                    # The physical book inside it still has two square pages.
                    ratios = (1, 2) if role == "page" else (1,)
                    if image.format != "WEBP" or not any(
                        abs(image.width / image.height - ratio) <= 0.01 for ratio in ratios
                    ):
                        raise ValueError(f"Invalid reviewed asset: {path}")
                    image.verify()
            if args.check:
                if reference.read_bytes() != pt.read_bytes():
                    raise ValueError(f"Backend reference differs: {reference}")
            else:
                shutil.copyfile(pt, reference)
    for path, data in (
        (ASSETS / "book-designs-v6.json", designs),
        (WEB / "catalogModels.json", web),
        (WEB / "localizedExamples.json", localized),
    ):
        if args.check:
            if read(path) != data:
                raise ValueError(f"Registry is not reproducible: {path}")
        else:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps({"version": 6, "new_cartoon_books": 50, "web_images": 450, "check": args.check})
    )


if __name__ == "__main__":
    main()
