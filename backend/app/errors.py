"""Envelope estável de erros da API.

Todo erro HTTP (handlers e HTTPException) devolve o mesmo formato JSON para o
cliente mostrar mensagem previsível:

    {
      "detail": "<mensagem humana>",
      "error": {
        "code": "<código estável>",
        "message": "<mesma mensagem>",
        "status": <http status>,
        "details": <opcional — ex. lista de validação>
      }
    }

`detail` permanece string (compatível com o front que lê `.detail`).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.errors")

# Códigos estáveis por família (não espelham o texto livre de cada rota).
CODE_BY_STATUS: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    402: "payment_required",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    413: "payload_too_large",
    422: "validation_error",
    429: "too_many_requests",
    500: "internal_error",
}


def error_code_for_status(http_status: int) -> str:
    return CODE_BY_STATUS.get(http_status, f"http_{http_status}")


def _message_from_detail(detail: Any) -> str:
    """Normaliza FastAPI `detail` (str | list | dict) para string estável."""
    if detail is None:
        return "Erro"
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        parts: list[str] = []
        for item in detail:
            if isinstance(item, dict):
                loc = item.get("loc")
                msg = item.get("msg") or item.get("message")
                if loc and msg:
                    path = ".".join(str(p) for p in loc if p != "body")
                    parts.append(f"{path}: {msg}" if path else str(msg))
                elif msg:
                    parts.append(str(msg))
                else:
                    parts.append(str(item))
            else:
                parts.append(str(item))
        return "; ".join(parts) if parts else "Dados invalidos"
    if isinstance(detail, dict):
        for key in ("message", "msg", "detail", "error"):
            val = detail.get(key)
            if isinstance(val, str) and val:
                return val
        return str(detail)
    return str(detail)


def error_envelope(
    *,
    status_code: int,
    message: str,
    code: str | None = None,
    details: Any = None,
) -> dict[str, Any]:
    """Corpo JSON estável para respostas de erro."""
    body: dict[str, Any] = {
        "detail": message,
        "error": {
            "code": code or error_code_for_status(status_code),
            "message": message,
            "status": status_code,
        },
    }
    if details is not None:
        body["error"]["details"] = details
    return body


def error_response(
    *,
    status_code: int,
    message: str,
    code: str | None = None,
    details: Any = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=error_envelope(
            status_code=status_code,
            message=message,
            code=code,
            details=details,
        ),
        headers=headers,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    message = _message_from_detail(exc.detail)
    details = exc.detail if not isinstance(exc.detail, str) else None
    headers = getattr(exc, "headers", None)
    return error_response(
        status_code=exc.status_code,
        message=message,
        details=details,
        headers=dict(headers) if headers else None,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    raw = exc.errors()
    message = _message_from_detail(raw)
    return error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message=message or "Dados invalidos",
        code="validation_error",
        details=raw,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Em prod não vaza stack; mensagem genérica estável.
    logger.exception("unhandled %s %s", request.method, request.url.path)
    return error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="Erro interno",
        code="internal_error",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Instala handlers de envelope em uma app FastAPI."""
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
