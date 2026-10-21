"""Logging estruturado (JSON em prod) com request_id / job_id.

STO-29: logs correlacionaveis entre API e worker. Em `dev` o formato padrao
continua texto legivel; `LOG_FORMAT=json` ou `APP_ENV!=dev` ativa JSON.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.observability.context import bind_fields


class CorrelationFilter(logging.Filter):
    """Injeta request_id / job_id / service no LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        fields = bind_fields()
        record.request_id = fields.get("request_id")  # type: ignore[attr-defined]
        record.job_id = fields.get("job_id")  # type: ignore[attr-defined]
        record.service = fields.get("service")  # type: ignore[attr-defined]
        return True


class JsonFormatter(logging.Formatter):
    """Uma linha JSON por evento — amigavel a Render / Datadog / Loki."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        rid = getattr(record, "request_id", None)
        jid = getattr(record, "job_id", None)
        svc = getattr(record, "service", None)
        if rid:
            payload["request_id"] = rid
        if jid:
            payload["job_id"] = jid
        if svc:
            payload["service"] = svc
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    """Formato legivel com request_id quando presente."""

    def format(self, record: logging.LogRecord) -> str:
        rid = getattr(record, "request_id", None)
        jid = getattr(record, "job_id", None)
        prefix_parts: list[str] = []
        if rid:
            prefix_parts.append(f"rid={rid}")
        if jid:
            prefix_parts.append(f"jid={jid}")
        prefix = f"[{' '.join(prefix_parts)}] " if prefix_parts else ""
        base = super().format(record)
        # super ja inclui asctime/level/name/message; prefixamos correlacao.
        if prefix and " - " in base:
            # "2024-... INFO name - msg" -> injeta apos o level name
            return f"{prefix}{base}"
        return f"{prefix}{base}"


def configure_logging(*, level: str = "INFO", fmt: str = "text", service: str = "api") -> None:
    """Configura root logger. Idempotente o suficiente para API + worker."""
    from app.observability.context import set_service

    set_service(service)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(CorrelationFilter())
    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(TextFormatter("%(asctime)s %(levelname)s %(name)s - %(message)s"))
    root.addHandler(handler)

    # Uvicorn/access: herdam o mesmo formato.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True
