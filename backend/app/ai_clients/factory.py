"""Factory: resolve o provedor configurado por etapa (settings).

Imagem: somente `openai` (GPT Image). Video: somente `kling`.
Nomes legado (`nano-banana`, `veo`) levantam ValueError.
"""

from __future__ import annotations

from app.ai_clients.base import ImageProvider, TextProvider, VideoProvider
from app.ai_clients.image_openai import OpenAIImageProvider
from app.ai_clients.text_anthropic import AnthropicTextProvider
from app.ai_clients.video_kling import KlingVideoProvider
from app.config import settings

_IMAGE = {"openai": OpenAIImageProvider}
_TEXT = {"claude": AnthropicTextProvider}
_VIDEO = {"kling": KlingVideoProvider}


def get_image_provider(name: str | None = None) -> ImageProvider:
    key = name or settings.image_provider
    try:
        return _IMAGE[key]()
    except KeyError:
        raise ValueError(f"ImageProvider desconhecido: {key}")


def get_text_provider(name: str | None = None) -> TextProvider:
    key = name or settings.text_provider
    try:
        return _TEXT[key]()
    except KeyError:
        raise ValueError(f"TextProvider desconhecido: {key}")


def get_video_provider(name: str | None = None) -> VideoProvider:
    key = name or settings.video_provider
    try:
        return _VIDEO[key]()
    except KeyError:
        raise ValueError(f"VideoProvider desconhecido: {key}")
