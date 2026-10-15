"""Worker job handlers package (split by job family).

Public API matches the former monolithic ``app.workers.handlers`` module:
``HANDLERS`` for the runner, plus helpers/scripts/tests import from here.
"""

from __future__ import annotations

from app import storage
from app.ai_clients import get_image_provider, get_text_provider, get_video_provider
from app.ai_clients.face_match import score_face_match
from app.config import settings

from .avatar import (
    AVATAR_FACE_JUDGE_ERROR,
    _lock_avatar_identity,
    _refine_identity,
    _refine_scene,
    handle_avatar,
    handle_extra_character,
    handle_realistic,
)
from .common import (
    _ext,
    _parse_pages,
    _parse_title,
    _payload,
    _project,
    _set_status,
    _short_captions,
    _tag_image,
)
from .ebook import handle_ebook
from .narrated import handle_narrated_video
from .story import (
    ensure_page_briefs,
    handle_story,
    handle_storyboard,
    lock_page_identity,
)
from .video import _clamp_kling_duration, _use_video_offline, handle_video

HANDLERS = {
    "AVATAR": handle_avatar,
    "REALISTIC": handle_realistic,
    "STORY": handle_story,
    "EBOOK": handle_ebook,
    "STORYBOARD": handle_storyboard,
    "VIDEO": handle_video,
    "NARRATED_VIDEO": handle_narrated_video,
    "EXTRA_CHARACTER": handle_extra_character,
}

__all__ = [
    "HANDLERS",
    "handle_avatar",
    "handle_realistic",
    "handle_story",
    "handle_ebook",
    "handle_storyboard",
    "handle_video",
    "handle_narrated_video",
    "handle_extra_character",
    "lock_page_identity",
    "ensure_page_briefs",
    "_parse_pages",
    "_parse_title",
    "_payload",
    "_project",
    "_set_status",
    "_short_captions",
    "_tag_image",
    "_ext",
    "_refine_identity",
    "_refine_scene",
    "_lock_avatar_identity",
    "AVATAR_FACE_JUDGE_ERROR",
    "_clamp_kling_duration",
    "_use_video_offline",
    "get_image_provider",
    "get_text_provider",
    "get_video_provider",
    "score_face_match",
    "settings",
    "storage",
]
