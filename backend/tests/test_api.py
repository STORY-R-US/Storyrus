"""Testes do fluxo: auth, creditos, idempotencia, backpressure, ownership."""

from tests.conftest import mint_guest, signup_and_verify


def test_health(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "elevenlabs_api_key", "sk-test-eleven")
    monkeypatch.setattr(settings, "resend_api_key", "")
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert "env" in body
    assert body["email_configured"] is False
    # STO-28: /health nao deve vazar se ElevenLabs (ou outros vendors) estao ligados.
    assert "has_elevenlabs" not in body
    assert "elevenlabs" not in body


def test_health_email_configured_when_resend_key_set(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "resend_api_key", "re_test_key")
    body = client.get("/health").json()
    assert body["email_configured"] is True


def test_signup_gives_bonus_credits(client):
    token = signup_and_verify(client, "x@y.com")
    me = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["credits"] == 10  # SIGNUP_BONUS_CREDITS default
    assert me.json()["email_verified"] is True
    assert me.json()["full_name"] == "Ana Souza"


def test_unauthenticated_is_401(client):
    me = client.get("/v1/auth/me")
    assert me.status_code == 401
    assert client.post("/v1/projects", json={}).status_code == 401
    assert client.get("/v1/credits").status_code == 401


def test_guest_cannot_create_project(client):
    token = mint_guest(client)
    r = client.post("/v1/projects", json={}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    assert "Cadastro" in r.json()["detail"]


def test_accounts_are_isolated(client):
    ta = signup_and_verify(client, "a@x.com")
    tb = signup_and_verify(client, "b@x.com")
    assert ta != tb

    me_a = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {ta}"}).json()
    me_b = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {tb}"}).json()
    assert me_a["id"] != me_b["id"]
    assert me_a["is_guest"] is False
    assert me_a["credits"] == 10

    pid = client.post("/v1/projects", json={}, headers={"Authorization": f"Bearer {ta}"}).json()[
        "id"
    ]
    listed_b = client.get("/v1/projects", headers={"Authorization": f"Bearer {tb}"}).json()
    assert listed_b == []
    other = client.get(f"/v1/projects/{pid}", headers={"Authorization": f"Bearer {tb}"})
    assert other.status_code == 404


def test_grant_without_secret_is_forbidden(auth_client):
    r = auth_client.post("/v1/credits/grant", json={"amount": 5})
    assert r.status_code == 403
    assert auth_client.get("/v1/credits").json()["credits"] == 10


def test_grant_with_admin_secret(auth_client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "credit_grant_secret", "test-grant-secret")
    r = auth_client.post(
        "/v1/credits/grant",
        json={"amount": 5},
        headers={"X-Admin-Secret": "test-grant-secret"},
    )
    assert r.status_code == 200
    assert r.json()["credits"] == 15


def test_grant_wrong_secret_is_forbidden(auth_client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "credit_grant_secret", "test-grant-secret")
    r = auth_client.post(
        "/v1/credits/grant",
        json={"amount": 5},
        headers={"X-Admin-Secret": "nope"},
    )
    assert r.status_code == 403


def test_create_and_list_project(auth_client):
    r = auth_client.post("/v1/projects", json={"style": "cartoon"})
    assert r.status_code == 201
    pid = r.json()["id"]
    assert r.json()["status"] == "CREATED"
    lst = auth_client.get("/v1/projects").json()
    assert any(p["id"] == pid for p in lst)


def test_avatar_requires_photo(auth_client):
    pid = auth_client.post("/v1/projects", json={"style": "realistic"}).json()["id"]
    r = auth_client.post(f"/v1/projects/{pid}/avatar")
    assert r.status_code == 400  # sem foto


def _add_photo(auth_client, pid):
    return auth_client.post(
        f"/v1/projects/{pid}/photos", json={"content_type": "image/jpeg", "ext": "jpg"}
    )


def test_full_flow_does_not_debit_and_is_idempotent(auth_client):
    pid = auth_client.post("/v1/projects", json={"style": "realistic"}).json()["id"]
    assert _add_photo(auth_client, pid).status_code == 201

    before = auth_client.get("/v1/credits").json()["credits"]

    key = "idem-123"
    r1 = auth_client.post(f"/v1/projects/{pid}/avatar", headers={"Idempotency-Key": key})
    assert r1.status_code == 202
    job_id = r1.json()["job_id"]

    after = auth_client.get("/v1/credits").json()["credits"]
    assert after == before

    # Repetir com a mesma chave: mesmo job, saldo intacto.
    r2 = auth_client.post(f"/v1/projects/{pid}/avatar", headers={"Idempotency-Key": key})
    assert r2.status_code == 202
    assert r2.json()["job_id"] == job_id
    assert auth_client.get("/v1/credits").json()["credits"] == after


def test_backpressure_limit(auth_client):
    pid = auth_client.post("/v1/projects", json={"style": "anime"}).json()["id"]
    _add_photo(auth_client, pid)
    # MAX_CONCURRENT_JOBS_PER_USER default = 4
    assert (
        auth_client.post(f"/v1/projects/{pid}/avatar", headers={"Idempotency-Key": "a"}).status_code
        == 202
    )
    assert (
        auth_client.post(
            f"/v1/projects/{pid}/realistic", headers={"Idempotency-Key": "b"}
        ).status_code
        == 202
    )
    assert (
        auth_client.post(f"/v1/projects/{pid}/story", headers={"Idempotency-Key": "c"}).status_code
        == 202
    )
    assert (
        auth_client.post(f"/v1/projects/{pid}/ebook", headers={"Idempotency-Key": "d"}).status_code
        == 202
    )
    r5 = auth_client.post(f"/v1/projects/{pid}/story", headers={"Idempotency-Key": "e"})
    assert r5.status_code == 429
    body = r5.json()
    assert "gerações em andamento" in body["detail"]
    assert body["error"]["code"] == "too_many_requests"
    assert body["error"]["status"] == 429
    assert body["error"]["message"] == body["detail"]


def test_video_jobs_count_towards_backpressure(auth_client, monkeypatch):
    """VIDEO / NARRATED_VIDEO entram no mesmo teto de concorrência (STO-17)."""
    from app.config import settings

    monkeypatch.setattr(settings, "credit_grant_secret", "test-grant-secret")
    pid = auth_client.post("/v1/projects", json={"style": "anime"}).json()["id"]
    _add_photo(auth_client, pid)
    # Creditos extras: video custa 5; precisamos de varios jobs ativos.
    assert (
        auth_client.post(
            "/v1/credits/grant",
            json={"amount": 50},
            headers={"X-Admin-Secret": "test-grant-secret"},
        ).status_code
        == 200
    )
    assert (
        auth_client.post(
            f"/v1/projects/{pid}/video", json={}, headers={"Idempotency-Key": "v1"}
        ).status_code
        == 202
    )
    assert (
        auth_client.post(f"/v1/projects/{pid}/avatar", headers={"Idempotency-Key": "a"}).status_code
        == 202
    )
    assert (
        auth_client.post(
            f"/v1/projects/{pid}/realistic", headers={"Idempotency-Key": "b"}
        ).status_code
        == 202
    )
    assert (
        auth_client.post(f"/v1/projects/{pid}/story", headers={"Idempotency-Key": "c"}).status_code
        == 202
    )
    # 4 ativos (1 video + 3 outros) — o proximo deve bater no limite.
    r5 = auth_client.post(f"/v1/projects/{pid}/ebook", headers={"Idempotency-Key": "d"})
    assert r5.status_code == 429
    assert r5.json()["error"]["code"] == "too_many_requests"


def test_generation_does_not_spend_credits(auth_client):
    pid = auth_client.post("/v1/projects", json={"style": "realistic"}).json()["id"]
    _add_photo(auth_client, pid)
    before = auth_client.get("/v1/credits").json()["credits"]
    r1 = auth_client.post(f"/v1/projects/{pid}/video", json={}, headers={"Idempotency-Key": "v1"})
    r2 = auth_client.post(f"/v1/projects/{pid}/video", json={}, headers={"Idempotency-Key": "v2"})
    r3 = auth_client.post(f"/v1/projects/{pid}/video", json={}, headers={"Idempotency-Key": "v3"})
    assert r1.status_code == 202 and r2.status_code == 202 and r3.status_code == 202
    assert auth_client.get("/v1/credits").json()["credits"] == before


def test_insufficient_credits_when_enabled(auth_client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "credits_enabled", True)
    pid = auth_client.post("/v1/projects", json={"style": "realistic"}).json()["id"]
    _add_photo(auth_client, pid)
    # Video custa 5; usuario tem 10. Dois videos cabem no teto de concorrencia (4)
    # e esgotam exatamente os creditos.
    r1 = auth_client.post(f"/v1/projects/{pid}/video", json={}, headers={"Idempotency-Key": "v1"})
    r2 = auth_client.post(f"/v1/projects/{pid}/video", json={}, headers={"Idempotency-Key": "v2"})
    assert r1.status_code == 202 and r2.status_code == 202
    assert auth_client.get("/v1/credits").json()["credits"] == 0
    r3 = auth_client.post(f"/v1/projects/{pid}/video", json={}, headers={"Idempotency-Key": "v3"})
    assert r3.status_code == 402
    body = r3.json()
    assert body["error"]["code"] == "payment_required"
    assert body["detail"] == body["error"]["message"]


def test_create_defaults_to_cgi_3d(auth_client):
    r = auth_client.post("/v1/projects", json={})
    assert r.status_code == 201
    assert r.json()["style"] == "cgi_3d"
    assert r.json()["character_approved_at"] is None
    assert r.json()["print_status"] is None


def test_approve_and_print_require_preview(auth_client):
    pid = auth_client.post("/v1/projects", json={}).json()["id"]
    assert auth_client.post(f"/v1/projects/{pid}/avatar/approve").status_code == 400
    assert auth_client.post(f"/v1/projects/{pid}/book/approve").status_code == 400
    assert auth_client.post(f"/v1/projects/{pid}/print-request").status_code == 400


def test_cannot_access_others_project(client):
    ta = signup_and_verify(client, "owner@x.com")
    pid = client.post(
        "/v1/projects",
        json={"style": "realistic"},
        headers={"Authorization": f"Bearer {ta}"},
    ).json()["id"]
    tb = signup_and_verify(client, "other@x.com")
    r = client.get(f"/v1/projects/{pid}", headers={"Authorization": f"Bearer {tb}"})
    assert r.status_code == 404
