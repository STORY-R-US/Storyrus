"""Middleware FastAPI: X-Request-ID em toda request.

Gera UUID se o cliente nao enviar; ecoa no response e liga o contextvar
para logs estruturados (STO-29).
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.observability.context import REQUEST_ID_HEADER, correlation_scope


def _normalize_request_id(raw: str | None) -> str:
    cleaned = (raw or "").strip()
    if not cleaned:
        return str(uuid.uuid4())
    # Limite defensivo: evita header gigante em logs.
    return cleaned[:128]


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = _normalize_request_id(request.headers.get(REQUEST_ID_HEADER))
        with correlation_scope(request_id=request_id, service="api"):
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
