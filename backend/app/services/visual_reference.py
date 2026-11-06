"""Public catalog and encrypted private visual guides; never customer identity sources."""

import hashlib
import unicodedata
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.ai_clients.base import ProviderError
from app.config import settings

ROOT = Path(__file__).resolve().parents[1] / "assets/composition_examples"
CATALOG_ROOT = ROOT / "catalog"


def catalog_family(style, theme):
    value = "".join(
        c for c in unicodedata.normalize("NFKD", theme.casefold()) if not unicodedata.combining(c)
    )
    if style == "cartoon":
        return "cartoon"
    if any(word in value for word in ("computador", "computer", "ordenador", "informatica")):
        return "creative"
    if any(
        word in value
        for word in (
            "bisavo",
            "bisabu",
            "mae",
            "mother",
            "madre",
            "vovo",
            "grandm",
            "abuela",
            "amor de",
            "familia",
        )
    ):
        return "family"
    return "adventure"


def load(stage, style, theme=""):
    if theme:
        family = catalog_family(style, theme)
        if family == "creative" and stage == "holding":
            return (CATALOG_ROOT / "family-holding.jpg").read_bytes()
        if family != "creative":
            role = stage if stage in {"cover", "holding"} else "page"
            suffix = "png" if family == "adventure" else "jpg"
            return (CATALOG_ROOT / f"{family}-{role}.{suffix}").read_bytes()
    if style == "cartoon" or not settings.editorial_visual_reference_key:
        return None
    role = "cover" if stage == "cover" else "page"
    try:
        data = Fernet(settings.editorial_visual_reference_key.encode()).decrypt(
            (ROOT / f"visual-master-{role}.enc").read_bytes()
        )
    except (ValueError, InvalidToken, OSError) as exc:
        raise ProviderError(
            "Referência visual indisponível; geração não iniciada", transient=False
        ) from exc
    return data


def fingerprint(style, theme=""):
    return {
        role: hashlib.sha256(data).hexdigest()
        for role in ("cover", "page")
        if (data := load(role, style, theme)) is not None
    }
