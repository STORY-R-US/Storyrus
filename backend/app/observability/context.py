"""Contexto de correlacao (request_id / job_id) via contextvars.

Usado pelo formatter JSON e pelo middleware da API; o worker liga os mesmos
campos ao processar um job para correlacionar logs API ↔ worker.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_job_id: ContextVar[str | None] = ContextVar("job_id", default=None)
_service: ContextVar[str | None] = ContextVar("service", default=None)

REQUEST_ID_HEADER = "X-Request-ID"


def get_request_id() -> str | None:
    return _request_id.get()


def get_job_id() -> str | None:
    return _job_id.get()


def get_service() -> str | None:
    return _service.get()


def set_request_id(value: str | None) -> Token:
    return _request_id.set(value)


def set_job_id(value: str | None) -> Token:
    return _job_id.set(value)


def set_service(value: str | None) -> Token:
    return _service.set(value)


def reset_request_id(token: Token) -> None:
    _request_id.reset(token)


def reset_job_id(token: Token) -> None:
    _job_id.reset(token)


def reset_service(token: Token) -> None:
    _service.reset(token)


def bind_fields(*, request_id: str | None = None, job_id: str | None = None) -> dict:
    """Snapshot dos campos de correlacao para logs / Opik metadata."""
    rid = request_id if request_id is not None else get_request_id()
    jid = job_id if job_id is not None else get_job_id()
    out: dict[str, str] = {}
    if rid:
        out["request_id"] = rid
    if jid:
        out["job_id"] = jid
    svc = get_service()
    if svc:
        out["service"] = svc
    return out


@contextmanager
def correlation_scope(
    *,
    request_id: str | None = None,
    job_id: str | None = None,
    service: str | None = None,
) -> Iterator[None]:
    """Liga campos de correlacao no escopo atual (API request ou worker job)."""
    tokens: list[tuple[str, Token]] = []
    if request_id is not None:
        tokens.append(("request_id", set_request_id(request_id)))
    if job_id is not None:
        tokens.append(("job_id", set_job_id(job_id)))
    if service is not None:
        tokens.append(("service", set_service(service)))
    try:
        yield
    finally:
        for name, token in reversed(tokens):
            if name == "request_id":
                reset_request_id(token)
            elif name == "job_id":
                reset_job_id(token)
            else:
                reset_service(token)
