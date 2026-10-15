"""STO-38: video e Kling-only — sem placeholder Veo."""

import pytest

from app.ai_clients.factory import get_video_provider
from app.ai_clients.video_kling import KlingVideoProvider
from app.config import Settings


def test_settings_has_no_veo_api_key():
    assert not hasattr(Settings(), "veo_api_key")


def test_default_video_provider_is_kling():
    assert Settings().video_provider == "kling"


def test_get_video_provider_returns_kling():
    provider = get_video_provider("kling")
    assert isinstance(provider, KlingVideoProvider)
    assert provider.name == "kling"


def test_unknown_video_provider_raises():
    with pytest.raises(ValueError, match="VideoProvider desconhecido"):
        get_video_provider("veo")
