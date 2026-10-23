"""Fixtures: app + banco SQLite em memoria isolado por teste."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("IMAGE_PROVIDER", "openai")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import rate_limit
from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.services import webhook_auth


@pytest.fixture(autouse=True)
def _reset_guest_rate_limit():
    """Evita 429 cruzado entre testes (mesmo IP do TestClient)."""
    rate_limit.reset()
    yield
    rate_limit.reset()


@pytest.fixture(autouse=True)
def _reset_webhook_nonces():
    """Evita 401 de nonce reutilizado cruzado entre testes."""
    webhook_auth.reset()
    yield
    webhook_auth.reset()


@pytest.fixture(autouse=True)
def _no_insightface_in_suite(monkeypatch):
    """Suite nao carrega buffalo_l / InsightFace em PNG fake.

    Detect devolve lista vazia → recorte geometrico. Faces vazias → score None.
    Testes que precisam de InsightFace fazem monkeypatch de `_faces_in`.
    """
    monkeypatch.setattr(
        "app.ai_clients.face_detect.face_boxes",
        lambda _photo: [],
    )
    monkeypatch.setattr(
        "app.ai_clients.face_match._faces_in",
        lambda _data: [],
    )


@pytest.fixture(autouse=True)
def _demo_generation_in_tests(monkeypatch):
    """Offline test fixtures opt in explicitly; production defaults to OpenAI."""
    monkeypatch.setattr(settings, "offline_fallback", True)
    monkeypatch.setattr(settings, "skip_openai", False)


@pytest.fixture(autouse=True)
def _disable_opik(monkeypatch):
    """Opik opt-in: testes nao enviam traces mesmo com chave no .env."""
    monkeypatch.setattr(settings, "opik_api_key", None)
    monkeypatch.setattr(settings, "opik_url_override", None)


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _override():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def signup_payload(email: str, password: str = "password123", **overrides) -> dict:
    """Payload completo de cadastro (perfil + termos)."""
    body = {
        "email": email,
        "password": password,
        "password_confirm": password,
        "full_name": "Ana Souza",
        "phone": "11999999999",
        "postal_code": "01310100",
        "street": "Av Paulista",
        "number": "1000",
        "complement": "Sala 1",
        "district": "Bela Vista",
        "city": "Sao Paulo",
        "state": "SP",
        "country": "BR",
        "accept_terms": True,
    }
    body.update(overrides)
    return body


def signup_and_verify(client, email: str, password: str = "password123", **overrides) -> str:
    """Cadastra, verifica e-mail e devolve access_token."""
    r = client.post("/v1/auth/signup", json=signup_payload(email, password, **overrides))
    assert r.status_code == 201, r.text
    verify_token = r.json().get("verify_token")
    assert verify_token, r.text
    v = client.post("/v1/auth/verify-email", json={"token": verify_token})
    assert v.status_code == 200, v.text
    return v.json()["access_token"]


@pytest.fixture()
def auth_client(client):
    """Cliente com conta registrada e e-mail verificado."""
    token = signup_and_verify(client, "auth@example.com")
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture()
def guest_client(client):
    r = client.post("/v1/auth/guest")
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
