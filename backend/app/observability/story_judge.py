"""Juiz de historia (OpenAI chat) compartilhado entre o job e o script Opik."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from app.config import settings
from app.observability.opik_trace import enabled, log_feedback, track, update_span

logger = logging.getLogger(__name__)

SCORE_KEYS = ("coherence", "age_fit", "education", "format")
_OPENAI_CHAT = "https://api.openai.com/v1/chat/completions"


_JUDGE_PROMPT = """Voce e um editor de livros infantis. Avalie a HISTORIA abaixo
em relacao ao BRIEF. Responda SOMENTE com JSON valido, sem markdown:

{{
  "coherence": <0 a 1, enredo com comeco/meio/fim e paginas que se conectam>,
  "age_fit": <0 a 1, vocabulario e tema adequados a idade {age}>,
  "education": <0 a 1, ensina o tema de forma ludica sem tom de aula>,
  "format": <0 a 1, titulo + paginas no formato pedido, estrofes curtas>,
  "reason": "<uma frase objetiva>"
}}

IDADE: {age}
IDIOMA: {language}
TEMA: {theme}

BRIEF:
{brief}

HISTORIA:
{story}
"""


def parse_judge_payload(text: str) -> dict[str, Any] | None:
    """Extrai scores 0-1 e reason. None se o corpo nao for JSON utilizavel."""
    if not text or not str(text).strip():
        return None
    raw = str(text).strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
    data = _loads_json(raw)
    if data is None:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if match:
            data = _loads_json(match.group(0))
    if not isinstance(data, dict):
        return None
    scores: dict[str, Any] = {}
    for key in SCORE_KEYS:
        try:
            scores[key] = max(0.0, min(1.0, float(data[key])))
        except (KeyError, TypeError, ValueError):
            return None
    scores["reason"] = str(data.get("reason") or "")[:400]
    return scores


def _loads_json(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def build_judge_prompt(
    *,
    brief: str,
    story: str,
    age: int | None,
    language: str,
    theme: str,
) -> str:
    return _JUDGE_PROMPT.format(
        age=age if age is not None else "3-7",
        language=language or "pt-BR",
        theme=theme or "",
        brief=(brief or "")[:4000],
        story=(story or "")[:8000],
    )


def _extract_openai_text(data: dict) -> str:
    choices = data.get("choices") or []
    if not choices:
        return ""
    message = (choices[0] or {}).get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part) for part in content
        )
    return str(content or "")


@track(name="story_judge", type="llm", capture_input=False, capture_output=False)
async def score_story(
    *,
    brief: str,
    story: str,
    age: int | None = None,
    language: str = "pt-BR",
    theme: str = "",
) -> dict[str, Any] | None:
    """Chama OpenAI chat. None se a chave faltar ou a resposta for ilegivel."""
    api_key = (settings.openai_api_key or "").strip()
    if not api_key:
        return None
    model = settings.openai_story_judge_model
    prompt = build_judge_prompt(brief=brief, story=story, age=age, language=language, theme=theme)
    update_span(
        metadata={
            "provider": "openai",
            "model": model,
            "action": "story_judge",
        },
        input={"prompt": prompt},
    )
    payload = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "content-type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=settings.openai_timeout_s) as client:
            resp = await client.post(_OPENAI_CHAT, json=payload, headers=headers)
    except httpx.RequestError as exc:
        logger.warning("Juiz de historia, rede: %s", exc)
        return None
    if resp.status_code >= 400:
        logger.warning("Juiz de historia %s: %s", resp.status_code, resp.text[:300])
        return None
    try:
        parsed = parse_judge_payload(_extract_openai_text(resp.json()))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Juiz de historia devolveu resposta ilegivel: %s", exc)
        return None
    if parsed is None:
        logger.warning("Juiz de historia: JSON sem scores utilizaveis")
        return None
    update_span(output=parsed)
    return parsed


async def score_and_log_story(
    *,
    brief: str,
    story: str,
    age: int | None = None,
    language: str = "pt-BR",
    theme: str = "",
) -> dict[str, Any] | None:
    """Avalia e grava feedback no trace. Nunca levanta."""
    if not settings.opik_eval_story or not enabled():
        return None
    try:
        scores = await score_story(
            brief=brief, story=story, age=age, language=language, theme=theme
        )
    except Exception:  # noqa: BLE001 - juiz nunca deve derrubar o job
        logger.warning("Juiz de historia falhou; job segue", exc_info=True)
        return None
    if not scores:
        return None
    reason = str(scores.get("reason") or "")
    for key in SCORE_KEYS:
        log_feedback(key, float(scores[key]), reason=reason)
    return scores
