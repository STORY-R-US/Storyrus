"""Linhas do extrato: append/merge/flush."""

from app.ai_clients.base import ImageResult
from app.services.usage_ledger import (
    append_usage,
    image_provider_name,
    lines_of,
    merge_usage,
    usage_line,
)


def test_append_and_merge_usage_lines():
    first = ImageResult(image_bytes=b"a", cost_usd=0.039, meta={"provider": "gemini"})
    append_usage(
        first,
        usage_line(action="generate_scene", label="Página 1 — geração", cost_usd=0.039),
    )
    second = ImageResult(image_bytes=b"b", cost_usd=0.039, meta={"provider": "gemini"})
    append_usage(
        second,
        usage_line(action="refine_scene", label="Página 1 — refine", cost_usd=0.039),
    )
    merge_usage(first, second)
    labels = [ln["label"] for ln in lines_of(second)]
    assert labels == ["Página 1 — geração", "Página 1 — refine"]


def test_image_provider_name_maps_aliases():
    r = ImageResult(image_bytes=b"x", meta={"head_provider": "pulid"})
    assert image_provider_name(r) == "fal"
    r2 = ImageResult(image_bytes=b"y", meta={"provider": "nano-banana"})
    assert image_provider_name(r2) == "gemini"
    r3 = ImageResult(image_bytes=b"z", meta={"provider": "openai"})
    assert image_provider_name(r3) == "openai"
