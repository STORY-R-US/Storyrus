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
import uuid
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


def _remember(request: Request, status_code: int, message: str) -> None:
    """Guarda o erro do ensaio no relatório. A resposta ao cliente segue igual."""
    if status_code not in {400, 409, 422, 500, 503}:
        return
    parts = [part for part in request.url.path.split("/") if part]
    if len(parts) < 3 or parts[0] != "v1" or parts[1] != "projects":
        return
    try:
        project_id = uuid.UUID(parts[2])
    except ValueError:
        return
    try:
        from app.database import SessionLocal
        from app.services.error_report import record_error

        db = SessionLocal()
        try:
            record_error(
                db,
                message=message,
                project_id=project_id,
                stage=parts[-1][:32],
            )
            db.commit()
        finally:
            db.close()
    except Exception:
        logger.exception("relatorio de erro")


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    message = _message_from_detail(exc.detail)
    _remember(request, exc.status_code, message)
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
    _remember(request, status.HTTP_422_UNPROCESSABLE_ENTITY, message or "Dados invalidos")
    return error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message=message or "Dados invalidos",
        code="validation_error",
        details=raw,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled %s %s", request.method, request.url.path)
    from app.config import settings

    detail = f"{type(exc).__name__}: {exc}"[:500]
    _remember(request, status.HTTP_500_INTERNAL_SERVER_ERROR, detail)
    # No ensaio a tela mostra a falha. Fora dele a resposta continua genérica.
    message = detail if settings.skip_openai else "Erro interno"
    return error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message=message,
        code="internal_error",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Instala handlers de envelope em uma app FastAPI."""
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
