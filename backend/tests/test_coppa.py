"""Conta adulta e exclusão do projeto pelo responsável."""

from app.models import User
from tests.conftest import _db, signup_and_verify


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_studio_stays_closed_until_the_adult_confirms(client):
    token = signup_and_verify(client, "menor@example.com")
    db = _db(client)
    try:
        user = db.query(User).filter(User.email == "menor@example.com").one()
        user.adult_confirmed_at = None
        db.commit()
    finally:
        db.close()

    headers = _auth(token)
    denied = client.post("/v1/projects", json={}, headers=headers)
    assert denied.status_code == 403
    assert "18" in denied.json()["detail"]

    confirmed = client.patch("/v1/auth/me", headers=headers, json={"confirm_adult": True})
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["adult_confirmed_at"] is not None

    created = client.post("/v1/projects", json={"child_name": "Lila"}, headers=headers)
    assert created.status_code == 201, created.text
    project_id = created.json()["id"]

    removed = client.delete(f"/v1/projects/{project_id}", headers=headers)
    assert removed.status_code == 204
    assert client.get(f"/v1/projects/{project_id}", headers=headers).status_code == 404


def test_parent_cannot_delete_another_account_project(client):
    owner = signup_and_verify(client, "pai@example.com")
    other = signup_and_verify(client, "outro@example.com")
    created = client.post("/v1/projects", json={}, headers=_auth(owner))
    assert created.status_code == 201, created.text
    project_id = created.json()["id"]

    denied = client.delete(f"/v1/projects/{project_id}", headers=_auth(other))
    assert denied.status_code == 404
    assert client.get(f"/v1/projects/{project_id}", headers=_auth(owner)).status_code == 200
