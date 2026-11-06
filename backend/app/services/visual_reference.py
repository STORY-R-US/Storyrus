"""Private visual masters: encrypted at rest, never customer identity references."""

import hashlib
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from app.ai_clients.base import ProviderError
from app.config import settings

ROOT = Path(__file__).resolve().parents[1] / "assets/composition_examples"


def load(stage, style):
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


def fingerprint(style):
    return {
        role: hashlib.sha256(data).hexdigest()
        for role in ("cover", "page")
        if (data := load(role, style)) is not None
    }
