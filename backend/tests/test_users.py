"""API do painel de usuarios cadastrados."""

from app.config import settings
from app.database import get_db
from app.models import Project, User
from tests.conftest import mint_guest, signup_and_verify


def _session(client):
    gen = client.app.dependency_overrides[get_db]()
    return next(gen)


def _owner_headers(monkeypatch, password: str = "segredo") -> dict[str, str]:
    monkeypatch.setattr(settings, "usage_dashboard_password", password)
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    monkeypatch.setattr(settings, "usage_lockout_max_attempts", 10)
    return {"X-Usage-Password": password}


def test_users_without_password_still_rejects_anonymous(client, monkeypatch):
    monkeypatch.setattr(settings, "usage_dashboard_password", None)
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    monkeypatch.setattr(settings, "owner_emails", "")
    r = client.get("/v1/users")
    assert r.status_code == 401


def test_users_wrong_password_is_401(client, monkeypatch):
    _owner_headers(monkeypatch)
    r = client.get("/v1/users", headers={"X-Usage-Password": "errada"})
    assert r.status_code == 401


def test_users_lists_registered_only(auth_client, monkeypatch):
    headers = _owner_headers(monkeypatch)
    mint_guest(auth_client)

    r = auth_client.get("/v1/users", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] >= 1
    emails = [u["email"] for u in body["users"]]
    assert "auth@example.com" in emails
    assert all(not email.startswith("guest-") for email in emails)
    me = next(u for u in body["users"] if u["email"] == "auth@example.com")
    assert me["full_name"] == "Ana Souza"
    assert me["phone"] == "11999999999"
    assert me["email_verified"] is True
    assert me["city"] == "Sao Paulo"
    assert me["state"] == "SP"


def test_users_project_count(auth_client, monkeypatch):
    headers = _owner_headers(monkeypatch)
    created = auth_client.post("/v1/projects", json={"style": "cgi_3d"})
    assert created.status_code == 201, created.text
    created2 = auth_client.post("/v1/projects", json={"style": "cgi_3d"})
    assert created2.status_code == 201, created2.text

    r = auth_client.get("/v1/users", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    me = next(u for u in body["users"] if u["email"] == "auth@example.com")
    assert me["project_count"] == 2
    assert "credits" in me
    assert "created_at" in me
    assert "id" in me


def test_users_ordered_newest_first(client, monkeypatch):
    headers = _owner_headers(monkeypatch)
    signup_and_verify(client, "old@example.com")
    signup_and_verify(client, "new@example.com")

    # Ajusta created_at para garantir ordem (SQLite pode colapsar timestamps iguais).
    db = _session(client)
    try:
        older = db.query(User).filter(User.email == "old@example.com").one()
        newer = db.query(User).filter(User.email == "new@example.com").one()
        from datetime import UTC, datetime, timedelta

        older.created_at = datetime.now(UTC) - timedelta(days=2)
        newer.created_at = datetime.now(UTC) - timedelta(hours=1)
        db.commit()
    finally:
        db.close()

    r = client.get("/v1/users", headers=headers)
    assert r.status_code == 200, r.text
    emails = [u["email"] for u in r.json()["users"]]
    assert emails.index("new@example.com") < emails.index("old@example.com")


def test_users_excludes_guest_seeded_directly(client, monkeypatch):
    headers = _owner_headers(monkeypatch)
    db = _session(client)
    try:
        db.add(
            User(
                email="guest-abc@storyrus.app",
                password_hash="!guest",
                credits=0,
            )
        )
        db.add(
            User(
                email="real@example.com",
                password_hash="hashed",
                credits=5,
                full_name="Real User",
                phone="11988887777",
                city="Recife",
                state="PE",
            )
        )
        db.flush()
        real = db.query(User).filter(User.email == "real@example.com").one()
        db.add(Project(user_id=real.id, status="CREATED"))
        db.commit()
    finally:
        db.close()

    r = client.get("/v1/users", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 1
    assert body["users"][0]["email"] == "real@example.com"
    assert body["users"][0]["full_name"] == "Real User"
    assert body["users"][0]["phone"] == "11988887777"
    assert body["users"][0]["project_count"] == 1
    assert body["users"][0]["credits"] == 5
    assert body["users"][0]["email_verified"] is False


def test_users_get_detail(auth_client, monkeypatch):
    headers = _owner_headers(monkeypatch)
    listed = auth_client.get("/v1/users", headers=headers).json()
    me = next(u for u in listed["users"] if u["email"] == "auth@example.com")
    r = auth_client.get(f"/v1/users/{me['id']}", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["email"] == "auth@example.com"
    assert body["street"] == "Av Paulista"
    assert body["postal_code"] == "01310100"
    assert body["number"] == "1000"
    assert body["district"] == "Bela Vista"
    assert body["country"] == "BR"
    assert body["terms_accepted_at"] is not None


def test_users_get_guest_is_404(auth_client, monkeypatch):
    headers = _owner_headers(monkeypatch)
    mint_guest(auth_client)
    db = _session(auth_client)
    try:
        guest = db.query(User).filter(User.password_hash == "!guest").one()
        guest_id = str(guest.id)
    finally:
        db.close()
    r = auth_client.get(f"/v1/users/{guest_id}", headers=headers)
    assert r.status_code == 404


def test_users_patch_profile_and_credits(auth_client, monkeypatch):
    headers = _owner_headers(monkeypatch)
    listed = auth_client.get("/v1/users", headers=headers).json()
    me = next(u for u in listed["users"] if u["email"] == "auth@example.com")
    r = auth_client.patch(
        f"/v1/users/{me['id']}",
        headers=headers,
        json={
            "full_name": "Ana Silva",
            "credits": 42,
            "city": "Campinas",
            "phone": "11911112222",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["full_name"] == "Ana Silva"
    assert body["credits"] == 42
    assert body["city"] == "Campinas"
    assert body["phone"] == "11911112222"
    assert body["street"] == "Av Paulista"


def test_users_patch_email_conflict(client, monkeypatch):
    headers = _owner_headers(monkeypatch)
    signup_and_verify(client, "one@example.com")
    signup_and_verify(client, "two@example.com")
    listed = client.get("/v1/users", headers=headers).json()
    one = next(u for u in listed["users"] if u["email"] == "one@example.com")
    r = client.patch(
        f"/v1/users/{one['id']}",
        headers=headers,
        json={"email": "two@example.com"},
    )
    assert r.status_code == 409


def test_users_patch_requires_password(auth_client, monkeypatch):
    _owner_headers(monkeypatch)
    listed = auth_client.get("/v1/users", headers={"X-Usage-Password": "segredo"}).json()
    me = listed["users"][0]
    r = auth_client.patch(f"/v1/users/{me['id']}", json={"credits": 1})
    assert r.status_code in {401, 503}


def test_users_delete_registered(auth_client, monkeypatch):
    headers = _owner_headers(monkeypatch)
    listed = auth_client.get("/v1/users", headers=headers).json()
    me = next(u for u in listed["users"] if u["email"] == "auth@example.com")
    created = auth_client.post("/v1/projects", json={"style": "cgi_3d"})
    assert created.status_code == 201, created.text

    r = auth_client.delete(f"/v1/users/{me['id']}", headers=headers)
    assert r.status_code == 204, r.text
    assert auth_client.get(f"/v1/users/{me['id']}", headers=headers).status_code == 404
    leftover = auth_client.get("/v1/users", headers=headers).json()
    assert all(u["email"] != "auth@example.com" for u in leftover["users"])
    db = _session(auth_client)
    try:
        assert db.query(User).filter(User.email == "auth@example.com").first() is None
        assert db.query(Project).count() == 0
    finally:
        db.close()


def test_users_delete_guest_is_404(auth_client, monkeypatch):
    headers = _owner_headers(monkeypatch)
    mint_guest(auth_client)
    db = _session(auth_client)
    try:
        guest = db.query(User).filter(User.password_hash == "!guest").one()
        guest_id = str(guest.id)
    finally:
        db.close()
    r = auth_client.delete(f"/v1/users/{guest_id}", headers=headers)
    assert r.status_code == 404


def test_users_delete_requires_password(auth_client, monkeypatch):
    _owner_headers(monkeypatch)
    listed = auth_client.get("/v1/users", headers={"X-Usage-Password": "segredo"}).json()
    me = listed["users"][0]
    r = auth_client.delete(f"/v1/users/{me['id']}")
    assert r.status_code in {401, 503}
