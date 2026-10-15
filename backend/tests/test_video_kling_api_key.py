"""Kling aceita KLING_API_KEY (Bearer novo) além do par legado AK/SK."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai_clients.video_kling import KlingVideoProvider
from app.config import Settings
from app.workers.handlers import video as video_handler


def test_settings_accepts_kling_api_key():
    s = Settings(kling_api_key="sk-test")
    assert s.kling_api_key == "sk-test"


def test_kling_configured_with_api_key_only(monkeypatch):
    monkeypatch.setattr(video_handler.settings, "kling_api_key", "sk-only")
    monkeypatch.setattr(video_handler.settings, "kling_access_key", None)
    monkeypatch.setattr(video_handler.settings, "kling_secret_key", None)
    assert video_handler._kling_configured() is True


def test_kling_configured_legacy_pair(monkeypatch):
    monkeypatch.setattr(video_handler.settings, "kling_api_key", None)
    monkeypatch.setattr(video_handler.settings, "kling_access_key", "ak")
    monkeypatch.setattr(video_handler.settings, "kling_secret_key", "sk")
    assert video_handler._kling_configured() is True


def test_kling_not_configured_without_creds(monkeypatch):
    monkeypatch.setattr(video_handler.settings, "kling_api_key", None)
    monkeypatch.setattr(video_handler.settings, "kling_access_key", None)
    monkeypatch.setattr(video_handler.settings, "kling_secret_key", None)
    assert video_handler._kling_configured() is False


def test_provider_prefers_api_key_auth():
    p = KlingVideoProvider(api_key="sk-bearer", access_key="ak", secret_key="sk")
    assert p.uses_api_key is True
    headers = p._headers()
    assert headers["Authorization"] == "Bearer sk-bearer"


def test_provider_falls_back_to_jwt_when_no_api_key():
    p = KlingVideoProvider(api_key=None, access_key="ak", secret_key="sk")
    assert p.uses_api_key is False
    assert p._headers()["Authorization"].startswith("Bearer ")
    assert p._headers()["Authorization"] != "Bearer ak"


@pytest.mark.asyncio
async def test_create_and_poll_new_api():
    create_resp = MagicMock()
    create_resp.status_code = 200
    create_resp.json.return_value = {
        "code": 0,
        "data": {"id": "task-1", "status": "submitted"},
    }

    poll_resp = MagicMock()
    poll_resp.status_code = 200
    poll_resp.json.return_value = {
        "code": 0,
        "data": [
            {
                "id": "task-1",
                "status": "succeeded",
                "outputs": [
                    {"type": "video", "url": "https://cdn/v.mp4", "duration": "5"},
                ],
            }
        ],
    }

    client = AsyncMock()
    client.post = AsyncMock(return_value=create_resp)
    client.get = AsyncMock(return_value=poll_resp)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)

    provider = KlingVideoProvider(api_key="sk-bearer", access_key=None, secret_key=None)
    with patch("httpx.AsyncClient", return_value=client):
        created = await provider.create_video(
            image=b"\x89PNG", prompt="gentle motion", duration_s=5
        )
        assert created.provider_task_id == "task-1"
        assert created.status == "PENDING"
        assert created.meta and created.meta.get("auth") == "api_key"

        done = await provider.poll_video(provider_task_id="task-1")
        assert done.status == "DONE"
        assert done.video_url == "https://cdn/v.mp4"

    post_url = client.post.await_args.args[0]
    assert post_url.endswith("/image-to-video/kling-2.6")
    body = client.post.await_args.kwargs["json"]
    assert body["contents"][0]["type"] == "prompt"
    assert body["contents"][1]["type"] == "first_frame"
    assert client.post.await_args.kwargs["headers"]["Authorization"] == "Bearer sk-bearer"
