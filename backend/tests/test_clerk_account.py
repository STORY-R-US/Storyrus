"""Ligação da sessão Clerk à linha local, sem trocar users.id."""

import base64
import hashlib
import hmac
import time
import uuid
from datetime import UTC, datetime

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt

from app.config import settings
from app.database import get_db
from app.models import Project, User
from app.services.clerk_identity import create_test_session_token
from tests.conftest import signup_and_verify


def _db(client):
    return next(client.app.dependency_overrides[get_db]())


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _legacy_user(client, email: str, *, credits: int, clerk_user_id: str | None) -> User:
    db = _db(client)
    try:
        user = User(
            email=email,
            password_hash="bcrypt-legacy",
            clerk_user_id=clerk_user_id,
            credits=credits,
            email_verified_at=datetime.now(UTC),
            terms_accepted_at=datetime.now(UTC),
            full_name="Ana Souza",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        project = Project(user_id=user.id, status="CREATED")
        db.add(project)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def test_existing_email_links_and_keeps_books(client):
    legacy = _legacy_user(client, "antiga@example.com", credits=77, clerk_user_id=None)
    token = create_test_session_token(
        clerk_user_id="user_link_antiga",
        email="Antiga@Example.com",
        email_verified=True,
    )
    me = client.get("/v1/auth/me", headers=_auth(token))
    assert me.status_code == 200, me.text
    body = me.json()
    assert body["id"] == str(legacy.id)
    assert body["credits"] == 77
    assert body["email"] == "antiga@example.com"
    projects = client.get("/v1/projects", headers=_auth(token))
    assert projects.status_code == 200, projects.text
    assert len(projects.json()) == 1

    db = _db(client)
    try:
        saved = db.get(User, legacy.id)
        assert saved is not None
        assert saved.clerk_user_id == "user_link_antiga"
        assert saved.password_hash == "bcrypt-legacy"
    finally:
        db.close()


def test_new_email_receives_signup_bonus_once(client, monkeypatch):
    monkeypatch.setattr(settings, "signup_bonus_credits", 10)
    token = create_test_session_token(
        clerk_user_id="user_nova",
        email="nova@example.com",
        email_verified=True,
    )
    first = client.get("/v1/auth/me", headers=_auth(token))
    assert first.status_code == 200, first.text
    assert first.json()["credits"] == 10
    again = client.get("/v1/auth/me", headers=_auth(token))
    assert again.json()["credits"] == 10
    assert again.json()["id"] == first.json()["id"]


def test_second_clerk_id_does_not_rebind(client):
    signup_and_verify(client, "ocupado@example.com")
    db = _db(client)
    try:
        user = db.query(User).filter(User.email == "ocupado@example.com").one()
        user.clerk_user_id = "user_original"
        db.add(user)
        db.commit()
        credits = user.credits
    finally:
        db.close()

    other = create_test_session_token(
        clerk_user_id="user_outro",
        email="ocupado@example.com",
        email_verified=True,
    )
    denied = client.get("/v1/auth/me", headers=_auth(other))
    assert denied.status_code == 409

    db = _db(client)
    try:
        saved = db.query(User).filter(User.email == "ocupado@example.com").one()
        assert saved.clerk_user_id == "user_original"
        assert saved.credits == credits
    finally:
        db.close()


def test_guest_email_is_not_linked(client):
    from tests.conftest import mint_guest

    mint_guest(client)
    db = _db(client)
    try:
        guest = db.query(User).filter(User.password_hash == "!guest").one()
        guest_email = guest.email
        guest_clerk = guest.clerk_user_id
    finally:
        db.close()

    token = create_test_session_token(
        clerk_user_id="user_nao_liga_guest",
        email=guest_email,
        email_verified=True,
    )
    denied = client.get("/v1/auth/me", headers=_auth(token))
    assert denied.status_code == 409
    db = _db(client)
    try:
        saved = db.query(User).filter(User.email == guest_email).one()
        assert saved.clerk_user_id == guest_clerk
        assert saved.password_hash == "!guest"
    finally:
        db.close()


def test_unverified_clerk_user_cannot_mutate(client):
    token = create_test_session_token(
        clerk_user_id="user_pendente",
        email="pendente@example.com",
        email_verified=False,
    )
    me = client.get("/v1/auth/me", headers=_auth(token))
    assert me.status_code == 200, me.text
    assert me.json()["email_verified"] is False
    denied = client.post("/v1/projects", json={}, headers=_auth(token))
    assert denied.status_code == 403
    assert "e-mail" in denied.json()["detail"].lower()


def test_profile_records_terms(client):
    token = signup_and_verify(client, "termos@example.com")
    db = _db(client)
    try:
        user = db.query(User).filter(User.email == "termos@example.com").one()
        user.terms_accepted_at = None
        db.add(user)
        db.commit()
    finally:
        db.close()
    r = client.patch(
        "/v1/auth/me",
        headers=_auth(token),
        json={"full_name": "Ana Souza", "accept_terms": True},
    )
    assert r.status_code == 200, r.text
    assert r.json()["terms_accepted_at"] is not None
    assert r.json()["full_name"] == "Ana Souza"


def test_prod_rejects_test_token(client, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "prod")
    monkeypatch.setattr(settings, "clerk_secret_key", "sk_test_clerk")
    monkeypatch.setattr("app.services.clerk_identity.fetch_jwks", lambda: [])
    token = jwt.encode(
        {
            "sub": "user_fake",
            "email": "fake@example.com",
            "email_verified": True,
            "purpose": "clerk_test",
        },
        "test-secret",
        algorithm="HS256",
    )
    denied = client.get("/v1/auth/me", headers=_auth(token))
    assert denied.status_code == 401


def _b64u(value: int) -> str:
    length = (value.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(value.to_bytes(length, "big")).rstrip(b"=").decode()


def test_clerk_jwt_creates_user_from_backend_email(client, monkeypatch):
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = private.public_key().public_numbers()
    kid = "kid-test"
    jwk = {
        "kty": "RSA",
        "kid": kid,
        "alg": "RS256",
        "use": "sig",
        "n": _b64u(numbers.n),
        "e": _b64u(numbers.e),
    }
    pem = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    token = jwt.encode(
        {"sub": "user_rs256", "iat": int(time.time()), "exp": int(time.time()) + 600},
        pem.decode(),
        algorithm="RS256",
        headers={"kid": kid},
    )
    monkeypatch.setattr(settings, "app_env", "prod")
    monkeypatch.setattr(settings, "clerk_secret_key", "sk_test_clerk")
    monkeypatch.setattr("app.services.clerk_identity.fetch_jwks", lambda: [jwk])
    monkeypatch.setattr(
        "app.services.clerk_identity.fetch_clerk_user",
        lambda user_id: {
            "id": user_id,
            "primary_email_address_id": "idn_1",
            "email_addresses": [
                {
                    "id": "idn_1",
                    "email_address": "RS256@Example.com",
                    "verification": {"status": "verified"},
                }
            ],
        },
    )
    me = client.get("/v1/auth/me", headers=_auth(token))
    assert me.status_code == 200, me.text
    assert me.json()["email"] == "rs256@example.com"
    assert me.json()["email_verified"] is True
    assert me.json()["credits"] == settings.signup_bonus_credits


def _sign_svix(secret: str, body: bytes, svix_id: str, timestamp: str) -> str:
    raw = secret.removeprefix("whsec_")
    key = base64.b64decode(raw + "=" * (-len(raw) % 4))
    signed = f"{svix_id}.{timestamp}.".encode() + body
    digest = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
    return f"v1,{digest}"


def test_webhook_updates_email_and_delete_clears_link(client, monkeypatch):
    secret = "whsec_" + base64.b64encode(b"webhook-secret-key").decode()
    monkeypatch.setattr(settings, "clerk_webhook_secret", secret)
    legacy = _legacy_user(client, "webhook@example.com", credits=4, clerk_user_id="user_hook")
    body = (
        b'{"type":"user.updated","data":{"id":"user_hook",'
        b'"primary_email_address_id":"idn_1","email_addresses":[{'
        b'"id":"idn_1","email_address":"novo@example.com",'
        b'"verification":{"status":"verified"}}]}}'
    )
    svix_id = "msg_" + uuid.uuid4().hex
    timestamp = str(int(time.time()))
    signature = _sign_svix(secret, body, svix_id, timestamp)
    updated = client.post(
        "/v1/webhooks/clerk",
        content=body,
        headers={
            "svix-id": svix_id,
            "svix-timestamp": timestamp,
            "svix-signature": signature,
            "content-type": "application/json",
        },
    )
    assert updated.status_code == 200, updated.text
    db = _db(client)
    try:
        saved = db.get(User, legacy.id)
        assert saved is not None
        assert saved.email == "novo@example.com"
        assert saved.credits == 4
    finally:
        db.close()

    deleted_body = b'{"type":"user.deleted","data":{"id":"user_hook","deleted":true}}'
    svix_id = "msg_" + uuid.uuid4().hex
    timestamp = str(int(time.time()))
    deleted = client.post(
        "/v1/webhooks/clerk",
        content=deleted_body,
        headers={
            "svix-id": svix_id,
            "svix-timestamp": timestamp,
            "svix-signature": _sign_svix(secret, deleted_body, svix_id, timestamp),
            "content-type": "application/json",
        },
    )
    assert deleted.status_code == 200, deleted.text
    db = _db(client)
    try:
        saved = db.get(User, legacy.id)
        assert saved is not None
        assert saved.clerk_user_id is None
        assert db.query(Project).filter(Project.user_id == legacy.id).count() == 1
    finally:
        db.close()


def test_webhook_rejects_bad_signature(client, monkeypatch):
    monkeypatch.setattr(settings, "clerk_webhook_secret", "whsec_" + base64.b64encode(b"k").decode())
    r = client.post(
        "/v1/webhooks/clerk",
        content=b"{}",
        headers={
            "svix-id": "msg_1",
            "svix-timestamp": str(int(time.time())),
            "svix-signature": "v1,aaaa",
        },
    )
    assert r.status_code == 401
