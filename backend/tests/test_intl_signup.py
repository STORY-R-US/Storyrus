"""Endereço internacional no perfil (não só CEP/UF brasileiros)."""

from tests.conftest import signup_and_verify


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_profile_accepts_us_address(client):
    token = signup_and_verify(client, "usa@example.com")
    r = client.patch(
        "/v1/auth/me",
        headers=_auth(token),
        json={
            "postal_code": "10001",
            "street": "5th Ave",
            "number": "1",
            "district": "",
            "city": "New York",
            "state": "NY",
            "country": "us",
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["country"] == "US"
    assert data["postal_code"] == "10001"
    assert data["state"] == "NY"
    assert data["district"] is None


def test_profile_rejects_invalid_country(client):
    token = signup_and_verify(client, "bad@example.com")
    r = client.patch(
        "/v1/auth/me",
        headers=_auth(token),
        json={"country": "12"},
    )
    assert r.status_code == 422


def test_profile_accepts_short_intl_postal(client):
    token = signup_and_verify(client, "pt@example.com")
    r = client.patch(
        "/v1/auth/me",
        headers=_auth(token),
        json={
            "postal_code": "1000",
            "street": "Rua Augusta",
            "number": "24",
            "district": None,
            "city": "Lisboa",
            "state": "Lisboa",
            "country": "PT",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["postal_code"] == "1000"
    assert r.json()["country"] == "PT"
