"""STO-26: refresh, resume e upgrade guest → conta real."""

from datetime import UTC, datetime, timedelta

from jose import jwt

from app.config import settings
from app.security import create_access_token
from tests.conftest import signup_and_verify, signup_payload


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_refresh_extends_same_user(client):
    guest = client.post("/v1/auth/guest")
    assert guest.status_code == 201
    token = guest.json()["access_token"]
    me_before = client.get("/v1/auth/me", headers=_auth(token)).json()

    r = client.post("/v1/auth/refresh", headers=_auth(token))
    assert r.status_code == 200
    new_token = r.json()["access_token"]
    # Mesmo segundo → JWT pode coincidir; o importante e o user_id.
    me_after = client.get("/v1/auth/me", headers=_auth(new_token)).json()
    assert me_after["id"] == me_before["id"]
    assert me_after["is_guest"] is True
    assert client.post("/v1/auth/refresh", headers=_auth(new_token)).status_code == 200


def test_resume_expired_token_keeps_user_and_projects(client, monkeypatch):
    monkeypatch.setattr(settings, "access_token_ttl_min", 1)
    monkeypatch.setattr(settings, "guest_resume_grace_min", 60 * 24)

    token = signup_and_verify(client, "resume@example.com")
    me = client.get("/v1/auth/me", headers=_auth(token)).json()
    pid = client.post("/v1/projects", json={}, headers=_auth(token)).json()["id"]

    # Token com exp no passado, mas iat ainda dentro da janela de resume.
    past = datetime.now(UTC) - timedelta(hours=2)
    expired = jwt.encode(
        {
            "sub": me["id"],
            "iat": past,
            "exp": past + timedelta(minutes=1),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    assert client.get("/v1/auth/me", headers=_auth(expired)).status_code == 401

    r = client.post("/v1/auth/resume", json={"access_token": expired})
    assert r.status_code == 200
    resumed = r.json()["access_token"]
    me2 = client.get("/v1/auth/me", headers=_auth(resumed)).json()
    assert me2["id"] == me["id"]
    assert client.get(f"/v1/projects/{pid}", headers=_auth(resumed)).status_code == 200


def test_resume_rejects_too_old_token(client, monkeypatch):
    monkeypatch.setattr(settings, "access_token_ttl_min", 1)
    monkeypatch.setattr(settings, "guest_resume_grace_min", 10)

    guest = client.post("/v1/auth/guest")
    me = client.get("/v1/auth/me", headers=_auth(guest.json()["access_token"])).json()
    ancient = datetime.now(UTC) - timedelta(days=40)
    token = jwt.encode(
        {
            "sub": me["id"],
            "iat": ancient,
            "exp": ancient + timedelta(minutes=1),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    r = client.post("/v1/auth/resume", json={"access_token": token})
    assert r.status_code == 401


def test_upgrade_guest_keeps_user_id_and_credits(client):
    token = client.post("/v1/auth/guest").json()["access_token"]
    me = client.get("/v1/auth/me", headers=_auth(token)).json()
    assert me["is_guest"] is True
    credits_before = me["credits"]
    # Guest nao cria livro; apos upgrade+verify, mesmo user_id cria projetos.
    assert client.post("/v1/projects", json={}, headers=_auth(token)).status_code == 403

    r = client.post(
        "/v1/auth/upgrade",
        json=signup_payload("real@example.com"),
        headers=_auth(token),
    )
    assert r.status_code == 200
    verify_token = r.json()["verify_token"]
    assert verify_token
    verified = client.post("/v1/auth/verify-email", json={"token": verify_token})
    assert verified.status_code == 200
    upgraded = verified.json()["access_token"]

    me2 = client.get("/v1/auth/me", headers=_auth(upgraded)).json()
    assert me2["id"] == me["id"]
    assert me2["email"] == "real@example.com"
    assert me2["is_guest"] is False
    assert me2["credits"] == credits_before
    assert me2["full_name"] == "Ana Souza"
    pid = client.post("/v1/projects", json={}, headers=_auth(upgraded)).json()["id"]
    assert client.get(f"/v1/projects/{pid}", headers=_auth(upgraded)).status_code == 200

    # Login com a conta permanente funciona.
    login = client.post(
        "/v1/auth/login",
        json={"email": "real@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    assert (
        client.get("/v1/auth/me", headers=_auth(login.json()["access_token"])).json()["id"]
        == me["id"]
    )


def test_upgrade_rejects_non_guest(client):
    token = signup_and_verify(client, "a@b.com")
    r = client.post(
        "/v1/auth/upgrade",
        json=signup_payload("c@d.com"),
        headers=_auth(token),
    )
    assert r.status_code == 400


def test_upgrade_email_conflict(client):
    assert client.post("/v1/auth/signup", json=signup_payload("taken@x.com")).status_code == 201
    token = client.post("/v1/auth/guest").json()["access_token"]
    r = client.post(
        "/v1/auth/upgrade",
        json=signup_payload("taken@x.com"),
        headers=_auth(token),
    )
    assert r.status_code == 409


def test_me_reports_is_guest(client):
    guest_token = client.post("/v1/auth/guest").json()["access_token"]
    assert client.get("/v1/auth/me", headers=_auth(guest_token)).json()["is_guest"] is True

    token = signup_and_verify(client, "p@q.com")
    assert client.get("/v1/auth/me", headers=_auth(token)).json()["is_guest"] is False


def test_create_access_token_roundtrip():
    token = create_access_token("00000000-0000-0000-0000-000000000001")
    assert isinstance(token, str) and len(token) > 20
