"""Cadastro com endereço internacional (não só CEP/UF brasileiros)."""

from tests.conftest import signup_and_verify, signup_payload


def test_signup_accepts_us_address(client):
    body = signup_payload(
        "usa@example.com",
        postal_code="90210",
        street="Rodeo Dr",
        number="100",
        complement=None,
        district=None,
        city="Beverly Hills",
        state="California",
        country="us",
    )
    r = client.post("/v1/auth/signup", json=body)
    assert r.status_code == 201, r.text

    token = signup_and_verify(
        client,
        "usa2@example.com",
        postal_code="10001",
        street="5th Ave",
        number="1",
        district="",
        city="New York",
        state="NY",
        country="US",
    )
    me = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    data = me.json()
    assert data["country"] == "US"
    assert data["postal_code"] == "10001"
    assert data["state"] == "NY"
    assert data["district"] is None


def test_signup_rejects_invalid_country(client):
    body = signup_payload("bad@example.com", country="12")
    r = client.post("/v1/auth/signup", json=body)
    assert r.status_code == 422


def test_signup_rejects_short_postal_still_ok_for_intl_min(client):
    body = signup_payload(
        "pt@example.com",
        postal_code="1000",
        street="Rua Augusta",
        number="24",
        district=None,
        city="Lisboa",
        state="Lisboa",
        country="PT",
    )
    r = client.post("/v1/auth/signup", json=body)
    assert r.status_code == 201, r.text
