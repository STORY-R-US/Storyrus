"""STO-16: envelope estável de erros da API."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.errors import (
    _message_from_detail,
    error_envelope,
    register_exception_handlers,
    unhandled_exception_handler,
)


def test_error_envelope_shape():
    body = error_envelope(status_code=404, message="Projeto nao encontrado")
    assert body == {
        "detail": "Projeto nao encontrado",
        "error": {
            "code": "not_found",
            "message": "Projeto nao encontrado",
            "status": 404,
        },
    }


def test_error_envelope_with_details():
    details = [{"loc": ["body", "email"], "msg": "field required", "type": "missing"}]
    body = error_envelope(
        status_code=422,
        message="email: field required",
        code="validation_error",
        details=details,
    )
    assert body["detail"] == "email: field required"
    assert body["error"]["details"] == details
    assert body["error"]["code"] == "validation_error"


def test_message_from_validation_list():
    raw = [
        {"loc": ("body", "password"), "msg": "Field required", "type": "missing"},
        {
            "loc": ("body", "email"),
            "msg": "value is not a valid email address",
            "type": "value_error",
        },
    ]
    msg = _message_from_detail(raw)
    assert "password: Field required" in msg
    assert "email:" in msg


def test_message_from_detail_variants():
    assert _message_from_detail("ok") == "ok"
    assert _message_from_detail({"message": "x"}) == "x"
    assert _message_from_detail(None) == "Erro"


def test_http_exception_uses_envelope(client):
    r = client.get("/v1/credits")
    assert r.status_code == 401
    body = r.json()
    assert body["detail"] == "Nao autenticado"
    assert body["error"]["code"] == "unauthorized"
    assert body["error"]["message"] == "Nao autenticado"
    assert body["error"]["status"] == 401


def test_validation_error_uses_envelope(client):
    r = client.post("/v1/auth/signup", json={"email": "not-an-email", "password": "x"})
    assert r.status_code == 422
    body = r.json()
    assert isinstance(body["detail"], str)
    assert body["detail"]  # mensagem humana não vazia
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["status"] == 422
    assert body["error"]["message"] == body["detail"]
    assert isinstance(body["error"]["details"], list)


def test_unhandled_exception_uses_envelope():
    mini = FastAPI()
    register_exception_handlers(mini)

    @mini.get("/boom")
    def _boom():
        raise RuntimeError("segredo interno")

    with TestClient(mini, raise_server_exceptions=False) as c:
        r = c.get("/boom")
    assert r.status_code == 500
    body = r.json()
    assert body["detail"] == "Erro interno"
    assert body["error"]["code"] == "internal_error"
    assert "segredo" not in body["detail"].lower()
    assert "RuntimeError" not in str(body)


async def test_unhandled_handler_direct():
    from starlette.requests import Request

    scope = {"type": "http", "method": "GET", "path": "/", "headers": []}
    request = Request(scope)
    resp = await unhandled_exception_handler(request, RuntimeError("x"))
    assert resp.status_code == 500
    assert resp.body
