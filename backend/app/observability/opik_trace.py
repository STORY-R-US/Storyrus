"""Wrapper fino do Comet Opik: no-op sem credencial, sem bytes de imagem.

Os provedores falam HTTP via httpx (nao SDKs oficiais), entao o tracing e
manual: `@track` + metadata. `enabled()` olha settings em tempo de chamada
para testes poderem ligar/desligar sem reimportar.
"""

from __future__ import annotations

import functools
import inspect
import logging
import os
from typing import Any, Callable

from app.config import settings

logger = logging.getLogger(__name__)

_REDACT_KEYS = frozenset(
    {
        "data",
        "inline_data",
        "inlineData",
        "image_bytes",
        "reference_images",
        "reference_image_url",
        "face_image_0",
        "target_image",
        "photo",
        "character_ref",
        "illustration",
        "extra_refs",
    }
)
_MAX_STR = 4000
_ssl_hook_installed = False


def enabled() -> bool:
    """True quando ha chave Cloud ou URL de self-host."""
    key = (getattr(settings, "opik_api_key", None) or "").strip()
    url = (getattr(settings, "opik_url_override", None) or "").strip()
    return bool(key or url)


def _install_ssl_hook() -> None:
    """Ajusta TLS do Opik quando `OPIK_SSL_VERIFY=system|false`.

    Nesta maquina o antivirus reassina o trafego; o certifi do httpx falha.
    """
    global _ssl_hook_installed
    if _ssl_hook_installed:
        return
    verify = True
    raw = (getattr(settings, "opik_ssl_verify", None) or "true").strip().lower()
    if raw in ("false", "0", "no"):
        verify = False
    elif raw == "system":
        import ssl

        import certifi

        try:
            verify = ssl.create_default_context()
        except Exception:  # noqa: BLE001
            verify = certifi.where()
    if verify is True:
        _ssl_hook_installed = True
        return
    from opik.hooks.httpx_client_hook import HttpxClientHook, add_httpx_client_hook

    add_httpx_client_hook(
        HttpxClientHook(client_modifier=None, client_init_arguments={"verify": verify})
    )
    _ssl_hook_installed = True


def _resolve_workspace(requested: str | None) -> str | None:
    """Aceita maiusculas vs minusculas: o Cloud e case-sensitive na API."""
    raw = (requested or "").strip()
    if not raw or not settings.opik_api_key:
        return raw or None
    try:
        import opik.httpx_client as httpx_client

        client = httpx_client.get(
            workspace=None,
            api_key=settings.opik_api_key,
            check_tls_certificate=True,
            compress_json_requests=True,
        )
        with client:
            resp = client.get("https://www.comet.com/api/rest/v2/workspaces")
        names = (resp.json() or {}).get("workspaceNames") or []
        for name in names:
            if str(name).lower() == raw.lower():
                return str(name)
    except Exception:  # noqa: BLE001
        logger.debug("Nao deu para resolver workspace Opik", exc_info=True)
    return raw


def configure() -> None:
    """Exporta settings para o SDK e chama `opik.configure`. Sem efeito se desligado."""
    if not enabled():
        logger.info("Opik desligado (sem OPIK_API_KEY nem OPIK_URL_OVERRIDE)")
        return

    project = (settings.opik_project_name or "storyrus").strip() or "storyrus"
    os.environ["OPIK_PROJECT_NAME"] = project
    if settings.opik_api_key:
        os.environ["OPIK_API_KEY"] = settings.opik_api_key
    url = (settings.opik_url_override or "").strip()
    if url:
        os.environ["OPIK_URL_OVERRIDE"] = url.rstrip("/")

    try:
        import opik

        _install_ssl_hook()
        workspace = _resolve_workspace(settings.opik_workspace)
        if workspace:
            os.environ["OPIK_WORKSPACE"] = workspace
        kwargs: dict[str, Any] = {
            "project_name": project,
            "force": True,
        }
        if settings.opik_api_key:
            kwargs["api_key"] = settings.opik_api_key
        if workspace:
            kwargs["workspace"] = workspace
        if url:
            if "comet.com" not in url:
                kwargs["use_local"] = True
            kwargs["url"] = url
        try:
            opik.configure(**kwargs)
        except TypeError:
            kwargs.pop("url", None)
            kwargs.pop("force", None)
            opik.configure(**kwargs)
        logger.info("Opik configurado project=%s workspace=%s", project, workspace)
    except Exception:  # noqa: BLE001 - tracing nunca deve derrubar API/worker
        logger.exception("Falha ao configurar Opik; spans desta rodada podem nao sair")


def flush() -> None:
    if not enabled():
        return
    try:
        from opik.api_objects import opik_client

        opik_client.get_client_cached().flush()
    except Exception:  # noqa: BLE001
        try:
            import opik

            flusher = getattr(opik, "flush", None)
            if callable(flusher):
                flusher()
        except Exception:  # noqa: BLE001
            logger.debug("Opik flush ignorado", exc_info=True)


def redact(obj: Any, *, max_str: int = _MAX_STR) -> Any:
    """Remove bytes, data-URIs e campos de imagem; corta strings longas."""
    if isinstance(obj, (bytes, bytearray)):
        return f"<bytes {len(obj)}>"
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for key, value in obj.items():
            lowered = str(key).lower()
            if key in _REDACT_KEYS or lowered in _REDACT_KEYS:
                out[key] = "<redacted>"
                continue
            if isinstance(value, str) and value.startswith("data:"):
                out[key] = "<data-uri>"
                continue
            out[key] = redact(value, max_str=max_str)
        return out
    if isinstance(obj, list):
        return [redact(item, max_str=max_str) for item in obj]
    if isinstance(obj, str):
        if obj.startswith("data:"):
            return "<data-uri>"
        if len(obj) > max_str:
            return obj[:max_str] + "…"
        return obj
    return obj


def prompt_text_from_parts(parts: list[Any] | None) -> str:
    """Junta so os trechos `text` de um payload Gemini (ignora inline_data)."""
    texts: list[str] = []
    for part in parts or []:
        if isinstance(part, dict) and part.get("text"):
            texts.append(str(part["text"]))
    return "\n".join(texts)


def job_metadata(job: Any) -> dict[str, Any]:
    meta = {
        "job_id": str(getattr(job, "id", "") or ""),
        "job_type": getattr(job, "type", None),
        "project_id": str(getattr(job, "project_id", "") or ""),
        "attempts": getattr(job, "attempts", None),
    }
    rid = getattr(job, "request_id", None)
    if rid:
        meta["request_id"] = str(rid)
    return meta


def update_span(
    *,
    metadata: dict[str, Any] | None = None,
    input: Any = None,
    output: Any = None,
    tags: list[str] | None = None,
) -> None:
    if not enabled():
        return
    try:
        from opik import opik_context

        payload: dict[str, Any] = {}
        if metadata is not None:
            payload["metadata"] = redact(metadata)
        if input is not None:
            payload["input"] = redact(input)
        if output is not None:
            payload["output"] = redact(output)
        if tags:
            payload["tags"] = tags
        if payload:
            opik_context.update_current_span(**payload)
    except Exception:  # noqa: BLE001
        logger.debug("Opik update_span ignorado", exc_info=True)


def update_trace(
    *,
    metadata: dict[str, Any] | None = None,
    input: Any = None,
    output: Any = None,
    tags: list[str] | None = None,
) -> None:
    if not enabled():
        return
    try:
        from opik import opik_context

        payload: dict[str, Any] = {}
        if metadata is not None:
            payload["metadata"] = redact(metadata)
        if input is not None:
            payload["input"] = redact(input)
        if output is not None:
            payload["output"] = redact(output)
        if tags:
            payload["tags"] = tags
        if payload:
            opik_context.update_current_trace(**payload)
    except Exception:  # noqa: BLE001
        logger.debug("Opik update_trace ignorado", exc_info=True)


def log_feedback(name: str, value: float, *, reason: str = "") -> None:
    """Grava um feedback score no span e no trace atuais."""
    if not enabled():
        return
    try:
        score: dict[str, Any] = {"name": name, "value": float(value)}
        if reason:
            score["reason"] = reason[:400]
        from opik import opik_context

        opik_context.update_current_span(feedback_scores=[score])
        opik_context.update_current_trace(feedback_scores=[score])
    except Exception:  # noqa: BLE001
        logger.debug("Opik log_feedback ignorado", exc_info=True)


def _ensure_tracked(fn: Callable, track_kwargs: dict[str, Any]) -> Callable:
    cached = getattr(fn, "_opik_tracked", None)
    if cached is not None:
        return cached
    import opik

    wrapped = opik.track(**track_kwargs)(fn)
    setattr(fn, "_opik_tracked", wrapped)
    return wrapped


def track(func: Callable | None = None, **track_kwargs: Any) -> Callable:
    """Como `opik.track`, mas identidade quando Opik esta desligado."""

    def decorator(fn: Callable) -> Callable:
        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any):
                if not enabled():
                    return await fn(*args, **kwargs)
                return await _ensure_tracked(fn, track_kwargs)(*args, **kwargs)

            return async_wrapper

        @functools.wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any):
            if not enabled():
                return fn(*args, **kwargs)
            return _ensure_tracked(fn, track_kwargs)(*args, **kwargs)

        return sync_wrapper

    if func is not None:
        return decorator(func)
    return decorator
