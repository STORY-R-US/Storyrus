"""Local examples are complete, deduplicated and scoped to composition only."""

import hashlib
import json

import pytest

from app.services import composition_examples as examples


def test_example_catalogue_preserves_provenance_without_duplicate_payloads():
    manifest = json.loads((examples.ROOT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_count"] == 36
    assert manifest["unique_count"] == 26
    entries = manifest["examples"]
    assert sum(len(item["sources"]) for item in entries) == 36
    assert len({item["sha256"] for item in entries}) == len(entries)
    assert {item["layout"] for item in entries} == {
        "single_page_centered",
        "open_book_centered",
        "open_book_headed",
    }
    for item in entries:
        path = (examples.ROOT / item["path"]).resolve()
        assert path.is_relative_to(examples.ROOT.resolve())
        assert len(item["sha256"]) == 64
        # Original images are deliberately not shipped to the public repository.
        # When the local private library is present, verify every original as well.
        if path.exists():
            assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]


def test_layouts_do_not_mix_mockup_and_flat_page_or_add_unsolicited_headings():
    page = examples.context("page")
    spread = examples.context("open_book")
    left = examples.context("page", "left")
    assert page["layout"]["source"] == "flat individual square page"
    assert spread["layout"]["source"] == "two finished square pages placed side by side"
    assert "no added heading" in left["layout"]["text"]
    assert "do not define a new cover" in examples.context("cover")["layout"]["text"]
    rules = " ".join(page["principles"])
    assert "never" in rules.lower()
    assert "incidental objects" in rules
    assert "Original project photos alone define identity" in rules
    assert "Do not crop feet" in rules
    with pytest.raises(ValueError):
        examples.context("unknown")
