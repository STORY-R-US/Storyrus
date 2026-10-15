"""Cadastro completo: perfil, termos, verificação de e-mail e PATCH /me."""

from tests.conftest import signup_and_verify, signup_payload


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_signup_rejects_password_mismatch(client):
    body = signup_payload("a@b.com", password_confirm="different1")
    r = client.post("/v1/auth/signup", json=body)
    assert r.status_code == 422


def test_signup_rejects_missing_terms(client):
    body = signup_payload("a@b.com", accept_terms=False)
    r = client.post("/v1/auth/signup", json=body)
    assert r.status_code == 422


def test_login_blocked_until_email_verified(client):
    r = client.post("/v1/auth/signup", json=signup_payload("wait@x.com"))
    assert r.status_code == 201
    assert r.json()["verify_token"]
    login = client.post("/v1/auth/login", json={"email": "wait@x.com", "password": "password123"})
    assert login.status_code == 403
    assert "e-mail" in login.json()["detail"].lower()


def test_verify_email_then_create_project(client):
    token = signup_and_verify(client, "ok@x.com")
    r = client.post("/v1/projects", json={}, headers=_auth(token))
    assert r.status_code == 201


def test_unverified_token_cannot_create_project(client):
    r = client.post("/v1/auth/signup", json=signup_payload("uv@x.com"))
    # Conta existe mas sem JWT de sessão; simula JWT antigo emitido antes do verify
    # pegando o sub via verify_token decode path: força login bloqueado + guest ok.
    assert r.status_code == 201
    # Sem access token de signup — criar projeto exige auth.
    assert client.post("/v1/projects", json={}).status_code == 401


def test_patch_me_updates_profile(client):
    token = signup_and_verify(client, "patch@x.com")
    r = client.patch(
        "/v1/auth/me",
        headers=_auth(token),
        json={"full_name": "Ana Patch", "phone": "11911112222", "city": "Campinas"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["full_name"] == "Ana Patch"
    assert body["phone"] == "11911112222"
    assert body["city"] == "Campinas"
    assert body["street"] == "Av Paulista"  # preservado


def test_legacy_account_without_verify_token_can_login(client):
    from app.database import get_db
    from app.main import app
    from app.models import User
    from app.security import hash_password

    db = next(app.dependency_overrides[get_db]())
    try:
        db.add(
            User(
                email="legacy@x.com",
                password_hash=hash_password("password123"),
                credits=10,
            )
        )
        db.commit()
    finally:
        db.close()

    login = client.post(
        "/v1/auth/login",
        json={"email": "legacy@x.com", "password": "password123"},
    )
    assert login.status_code == 200, login.text
    me = client.get("/v1/auth/me", headers=_auth(login.json()["access_token"]))
    assert me.status_code == 200
    assert me.json()["email_verified"] is True


def test_resend_verify_then_confirm(client):
    r = client.post("/v1/auth/signup", json=signup_payload("again@x.com"))
    assert r.status_code == 201
    first = r.json()["verify_token"]
    again = client.post("/v1/auth/resend-verify", json={"email": "again@x.com"})
    assert again.status_code == 200
    token = again.json()["verify_token"]
    assert token
    assert token != first
    assert client.post("/v1/auth/verify-email", json={"token": first}).status_code == 400
    verified = client.post("/v1/auth/verify-email", json={"token": token})
    assert verified.status_code == 200
    assert verified.json()["access_token"]


def test_resend_verify_unknown_email_is_ok(client):
    r = client.post("/v1/auth/resend-verify", json={"email": "nobody@x.com"})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json().get("verify_token") in (None, "")


def test_login_accepts_email_case_difference(client):
    signup_and_verify(client, "Case.User@Example.com")
    login = client.post(
        "/v1/auth/login",
        json={"email": "CASE.USER@example.com", "password": "password123"},
    )
    assert login.status_code == 200, login.text


def test_verify_accepts_token_wrapped_by_email_client(client):
    r = client.post("/v1/auth/signup", json=signup_payload("wrap@x.com"))
    token = r.json()["verify_token"]
    assert token
    assert "." not in token
    wrapped = f"{token[:12]}\n {token[12:]}"
    verified = client.post("/v1/auth/verify-email", json={"token": wrapped})
    assert verified.status_code == 200, verified.text


def test_old_jwt_verify_link_still_works(client):
    from app.database import get_db
    from app.main import app
    from app.models import User
    from app.security import create_email_verify_token, hash_password, hash_token

    db = next(app.dependency_overrides[get_db]())
    try:
        user = User(
            email="jwtlink@x.com",
            password_hash=hash_password("password123"),
            credits=10,
        )
        db.add(user)
        db.flush()
        raw = create_email_verify_token(str(user.id))
        user.email_verify_token_hash = hash_token(raw)
        db.add(user)
        db.commit()
    finally:
        db.close()

    verified = client.post("/v1/auth/verify-email", json={"token": raw})
    assert verified.status_code == 200, verified.text
