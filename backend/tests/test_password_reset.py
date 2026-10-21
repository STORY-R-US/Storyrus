"""Testes de esqueci / redefinir senha."""

from app import rate_limit
from app.config import settings
from tests.conftest import signup_and_verify, signup_payload


def test_forgot_password_unknown_email_still_ok(client):
    r = client.post("/v1/auth/forgot-password", json={"email": "nobody@x.com"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert "redefinir" in body["message"].lower()
    assert body.get("reset_token") is None


def test_forgot_and_reset_password_flow(client):
    signup_and_verify(client, "reset@x.com", password="antiga1234")

    r = client.post("/v1/auth/forgot-password", json={"email": "reset@x.com"})
    assert r.status_code == 200, r.text
    reset_token = r.json().get("reset_token")
    assert reset_token, r.text
    assert "." not in reset_token

    bad = client.post(
        "/v1/auth/reset-password",
        json={
            "token": reset_token,
            "password": "nova12345",
            "password_confirm": "outra12345",
        },
    )
    assert bad.status_code == 422

    ok = client.post(
        "/v1/auth/reset-password",
        json={
            "token": reset_token,
            "password": "nova12345",
            "password_confirm": "nova12345",
        },
    )
    assert ok.status_code == 200, ok.text
    assert "access_token" in ok.json()

    # Token de reset é single-use.
    again = client.post(
        "/v1/auth/reset-password",
        json={
            "token": reset_token,
            "password": "outra9999",
            "password_confirm": "outra9999",
        },
    )
    assert again.status_code == 400

    old = client.post(
        "/v1/auth/login",
        json={"email": "reset@x.com", "password": "antiga1234"},
    )
    assert old.status_code == 401

    new = client.post(
        "/v1/auth/login",
        json={"email": "reset@x.com", "password": "nova12345"},
    )
    assert new.status_code == 200, new.text


def test_reset_verifies_unverified_account(client):
    r = client.post("/v1/auth/signup", json=signup_payload("pending@x.com"))
    assert r.status_code == 201
    forgot = client.post("/v1/auth/forgot-password", json={"email": "pending@x.com"})
    assert forgot.status_code == 200
    token = forgot.json().get("reset_token")
    assert token

    reset = client.post(
        "/v1/auth/reset-password",
        json={
            "token": token,
            "password": "nova12345",
            "password_confirm": "nova12345",
        },
    )
    assert reset.status_code == 200, reset.text

    login = client.post(
        "/v1/auth/login",
        json={"email": "pending@x.com", "password": "nova12345"},
    )
    assert login.status_code == 200, login.text


def test_reset_accepts_token_wrapped_by_email_client(client):
    signup_and_verify(client, "wrap@x.com", password="antiga1234")
    forgot = client.post("/v1/auth/forgot-password", json={"email": "wrap@x.com"})
    token = forgot.json()["reset_token"]
    wrapped = f"{token[:10]}\n {token[10:]}"
    ok = client.post(
        "/v1/auth/reset-password",
        json={
            "token": wrapped,
            "password": "nova12345",
            "password_confirm": "nova12345",
        },
    )
    assert ok.status_code == 200, ok.text


def test_old_jwt_reset_link_still_works(client):
    from app.database import get_db
    from app.main import app
    from app.models import User
    from app.security import create_password_reset_token, hash_token

    signup_and_verify(client, "jwtreset@x.com", password="antiga1234")
    db = next(app.dependency_overrides[get_db]())
    try:
        user = db.query(User).filter(User.email == "jwtreset@x.com").one()
        raw = create_password_reset_token(str(user.id))
        user.password_reset_token_hash = hash_token(raw)
        db.add(user)
        db.commit()
    finally:
        db.close()

    ok = client.post(
        "/v1/auth/reset-password",
        json={
            "token": raw,
            "password": "nova12345",
            "password_confirm": "nova12345",
        },
    )
    assert ok.status_code == 200, ok.text


def test_forgot_password_rate_limited(client, monkeypatch):
    rate_limit.reset()
    monkeypatch.setattr(settings, "password_reset_rate_limit_per_email", 2)
    monkeypatch.setattr(settings, "password_reset_rate_limit_per_ip", 100)
    email = {"email": "rl@x.com"}
    assert client.post("/v1/auth/forgot-password", json=email).status_code == 200
    assert client.post("/v1/auth/forgot-password", json=email).status_code == 200
    r = client.post("/v1/auth/forgot-password", json=email)
    assert r.status_code == 429
