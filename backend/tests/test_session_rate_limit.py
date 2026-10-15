"""Recuperar uma sessão não cria convidados nem deve gastar a cota deles."""

from app.config import settings
from tests.conftest import signup_and_verify


def test_resume_works_after_guest_creation_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "guest_rate_limit_per_ip", 1)
    token = client.post("/v1/auth/guest").json()["access_token"]

    for _ in range(12):
        assert client.post("/v1/auth/resume", json={"access_token": token}).status_code == 200
    assert client.post("/v1/auth/guest").status_code == 429


def test_resume_does_not_consume_guest_creation_allowance(client, monkeypatch):
    monkeypatch.setattr(settings, "guest_rate_limit_per_ip", 1)
    token = signup_and_verify(client, "session@example.com")

    for _ in range(3):
        assert client.post("/v1/auth/resume", json={"access_token": token}).status_code == 200
    assert client.post("/v1/auth/guest").status_code == 201


def test_invalid_resume_attempts_are_limited_by_ip(client, monkeypatch):
    monkeypatch.setattr(settings, "session_resume_rate_limit_per_ip", 1)
    monkeypatch.setattr(settings, "session_resume_rate_limit_window_s", 60)
    body = {"access_token": "invalid-session-token"}

    assert client.post("/v1/auth/resume", json=body).status_code == 401
    blocked = client.post("/v1/auth/resume", json=body)
    assert blocked.status_code == 429
    assert blocked.headers["Retry-After"] == "60"
    assert client.get("/health").status_code == 200


def test_resume_account_limit_does_not_block_other_accounts(client, monkeypatch):
    monkeypatch.setattr(settings, "session_resume_rate_limit_per_user", 1)
    first = signup_and_verify(client, "first@example.com")
    second = signup_and_verify(client, "second@example.com")

    assert client.post("/v1/auth/resume", json={"access_token": first}).status_code == 200
    blocked = client.post("/v1/auth/resume", json={"access_token": first})
    assert blocked.status_code == 429
    assert blocked.headers["Retry-After"] == "60"
    assert "conta" in blocked.json()["detail"]
    assert client.post("/v1/auth/resume", json={"access_token": second}).status_code == 200


def test_resume_limit_expires(client, monkeypatch):
    from app import rate_limit

    monkeypatch.setattr(settings, "session_resume_rate_limit_per_user", 1)
    monkeypatch.setattr(rate_limit, "_allow_redis", lambda *_args: None)
    token = signup_and_verify(client, "window@example.com")
    clock = [100.0]
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: clock[0])

    assert client.post("/v1/auth/resume", json={"access_token": token}).status_code == 200
    assert client.post("/v1/auth/resume", json={"access_token": token}).status_code == 429
    clock[0] += 61
    assert client.post("/v1/auth/resume", json={"access_token": token}).status_code == 200
