"""Papel is_admin nos painéis e fallback da senha compartilhada."""

from datetime import UTC, datetime

from app.config import settings
from app.database import get_db
from app.models import User
from tests.conftest import signup_and_verify


def _is_admin(client, email: str) -> bool:
    gen = client.app.dependency_overrides[get_db]()
    db = next(gen)
    try:
        user = db.query(User).filter(User.email == email).one()
        return bool(user.is_admin)
    finally:
        db.close()


def _set_admin(client, email: str, *, admin: bool) -> None:
    gen = client.app.dependency_overrides[get_db]()
    db = next(gen)
    try:
        user = db.query(User).filter(User.email == email).one()
        user.is_admin = admin
        if user.email_verified_at is None:
            user.email_verified_at = datetime.now(UTC)
        db.add(user)
        db.commit()
    finally:
        db.close()


def test_is_admin_opens_usage_without_password(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "usage_dashboard_password", None)
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    monkeypatch.setattr(settings, "owner_emails", "")
    monkeypatch.setattr(settings, "owner_password_fallback", False)
    _set_admin(auth_client, "auth@example.com", admin=True)

    ok = auth_client.get("/v1/usage")
    assert ok.status_code == 200, ok.text
    me = auth_client.get("/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["is_admin"] is True
    assert me.json()["is_owner"] is True


def test_owner_email_promotes_is_admin(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "usage_dashboard_password", None)
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    monkeypatch.setattr(settings, "owner_emails", "auth@example.com")
    monkeypatch.setattr(settings, "owner_password_fallback", False)
    _set_admin(auth_client, "auth@example.com", admin=False)

    ok = auth_client.get("/v1/usage")
    assert ok.status_code == 200, ok.text
    assert _is_admin(auth_client, "auth@example.com") is True


def test_password_rejected_when_fallback_off(client, monkeypatch):
    monkeypatch.setattr(settings, "usage_dashboard_password", "segredo")
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    monkeypatch.setattr(settings, "owner_emails", "")
    monkeypatch.setattr(settings, "owner_password_fallback", False)
    denied = client.get("/v1/usage", headers={"X-Usage-Password": "segredo"})
    assert denied.status_code == 401
    assert "administrador" in denied.json()["detail"].lower()


def test_non_admin_jwt_rejected_when_fallback_off(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "usage_dashboard_password", "segredo")
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    monkeypatch.setattr(settings, "owner_emails", "")
    monkeypatch.setattr(settings, "owner_password_fallback", False)
    denied = auth_client.get("/v1/usage")
    assert denied.status_code == 401


def test_builtin_owner_email_opens_usage_when_env_list_is_empty(client, monkeypatch):
    monkeypatch.setattr(settings, "usage_dashboard_password", None)
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    monkeypatch.setattr(settings, "owner_emails", "")
    monkeypatch.setattr(settings, "owner_password_fallback", False)
    token = signup_and_verify(client, "eng.andrevitor89@gmail.com")

    ok = client.get("/v1/usage", headers={"Authorization": f"Bearer {token}"})
    assert ok.status_code == 200, ok.text
    assert _is_admin(client, "eng.andrevitor89@gmail.com") is True


def test_gmail_dots_and_plus_match_builtin_owner(client, monkeypatch):
    monkeypatch.setattr(settings, "usage_dashboard_password", None)
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    monkeypatch.setattr(settings, "owner_emails", "")
    monkeypatch.setattr(settings, "owner_password_fallback", False)
    email = "eng.andre.vitor89+painel@gmail.com"
    token = signup_and_verify(client, email)

    assert _is_admin(client, email) is True
    ok = client.get("/v1/usage?scope=orders", headers={"Authorization": f"Bearer {token}"})
    assert ok.status_code == 200, ok.text


def test_login_promotes_gmail_owner_without_dots(client, monkeypatch):
    monkeypatch.setattr(settings, "usage_dashboard_password", None)
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    monkeypatch.setattr(settings, "owner_emails", "")
    monkeypatch.setattr(settings, "owner_password_fallback", False)
    email = "engandrevitor89@gmail.com"
    token = signup_and_verify(client, email)
    _set_admin(client, email, admin=False)
    assert _is_admin(client, email) is False

    me = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    assert _is_admin(client, email) is True
    ok = client.get(
        "/v1/usage?scope=orders",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ok.status_code == 200, ok.text


def test_non_gmail_local_part_is_not_folded(client, monkeypatch):
    monkeypatch.setattr(settings, "usage_dashboard_password", None)
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    monkeypatch.setattr(settings, "owner_emails", "")
    monkeypatch.setattr(settings, "owner_password_fallback", False)
    email = "eng.andrevitor89+painel@storyrus.ai"
    token = signup_and_verify(client, email)

    assert _is_admin(client, email) is False
    denied = client.get("/v1/usage", headers={"Authorization": f"Bearer {token}"})
    assert denied.status_code == 401


def test_password_still_works_when_fallback_on(client, monkeypatch):
    monkeypatch.setattr(settings, "usage_dashboard_password", "segredo")
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    monkeypatch.setattr(settings, "owner_emails", "")
    monkeypatch.setattr(settings, "owner_password_fallback", True)
    ok = client.get("/v1/usage", headers={"X-Usage-Password": "segredo"})
    assert ok.status_code == 200, ok.text
