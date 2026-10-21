"""STO-6: rate limit em POST /v1/auth/guest."""


def test_guest_rate_limit_by_ip(client, monkeypatch):
    from app import rate_limit
    from app.config import settings

    monkeypatch.setattr(settings, "guest_rate_limit_per_ip", 2)
    monkeypatch.setattr(settings, "guest_rate_limit_window_s", 3600)
    rate_limit.reset()

    assert client.post("/v1/auth/guest").status_code == 201
    assert client.post("/v1/auth/guest").status_code == 201
    r = client.post("/v1/auth/guest")
    assert r.status_code == 429
    assert "IP" in r.json()["detail"]


def test_guest_rate_limit_by_fingerprint(client, monkeypatch):
    from app import rate_limit
    from app.config import settings

    monkeypatch.setattr(settings, "guest_rate_limit_per_ip", 100)
    monkeypatch.setattr(settings, "guest_rate_limit_per_fingerprint", 1)
    monkeypatch.setattr(settings, "guest_rate_limit_window_s", 3600)
    rate_limit.reset()

    headers = {"X-Device-Fingerprint": "device-abc"}
    assert client.post("/v1/auth/guest", headers=headers).status_code == 201
    r = client.post("/v1/auth/guest", headers=headers)
    assert r.status_code == 429
    assert "dispositivo" in r.json()["detail"]


def test_guest_rate_limit_zero_disables_ip(client, monkeypatch):
    from app import rate_limit
    from app.config import settings

    monkeypatch.setattr(settings, "guest_rate_limit_per_ip", 0)
    monkeypatch.setattr(settings, "guest_rate_limit_window_s", 3600)
    rate_limit.reset()

    for _ in range(3):
        assert client.post("/v1/auth/guest").status_code == 201
