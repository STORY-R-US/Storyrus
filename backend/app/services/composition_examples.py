"""Private user-supplied examples translated into stage-specific composition rules.

No training, generation or network calls occur when reading this guide. Original
examples stay in the local private library and are never deployed or used as customer identity photos.
"""

import hashlib
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "assets/composition_examples"


@lru_cache(maxsize=1)
def guide():
    return json.loads((ROOT / "guide.json").read_text(encoding="utf-8"))


def context(stage, alignment="center"):
    data = guide()
    if stage == "open_book":
        layout = data["layouts"]["open_book_centered"]
    elif stage == "page":
        layout = data["layouts"]["single_page_centered"]
        if alignment == "left":
            layout = {
                **layout,
                "text": "Use the project's existing left-aligned body, with no added heading.",
            }
    elif stage == "cover":
        layout = {
            "source": "flat square cover",
            "text": "Keep the existing project cover title layout; the supplied examples do not define a new cover.",
        }
    else:
        raise ValueError("Unknown composition example stage")
    return {
        "version": data["version"],
        "stage": stage,
        "layout": layout,
        "principles": data["principles"],
    }


def signature():
    return hashlib.sha256((ROOT / "guide.json").read_bytes()).hexdigest()
