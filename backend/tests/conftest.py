"""Fixtures: app + banco SQLite em memoria isolado por teste."""

import os

os.environ["APP_ENV"] = "test"
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("IMAGE_PROVIDER", "openai")

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import rate_limit
from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import User
from app.owner_auth import promote_verified_owner
from app.services import webhook_auth
from app.services.clerk_identity import create_test_session_token


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


def _db(client):
    gen = client.app.dependency_overrides[get_db]()
    return next(gen)


def _blank_to_none(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        return None
    return value


def signup_and_verify(client, email: str, password: str = "password123", **overrides) -> str:
    """Cria a conta direto no banco e devolve um Bearer de teste do Clerk.

    `password` fica na assinatura para os testes antigos; a senha não é mais da API.
    """
    del password
    body = signup_payload(email, **overrides)
    db = _db(client)
    try:
        clerk_id = f"user_{uuid.uuid4().hex}"
        now = datetime.now(UTC)
        user = User(
            email=str(body["email"]).strip().lower(),
            password_hash="!clerk",
            clerk_user_id=clerk_id,
            credits=settings.signup_bonus_credits,
            email_verified_at=now,
            terms_accepted_at=now,
            adult_confirmed_at=now,
            full_name=body["full_name"],
            phone=body["phone"],
            postal_code=str(body["postal_code"]).strip(),
            street=body["street"],
            number=body["number"],
            complement=_blank_to_none(body.get("complement")),
            district=_blank_to_none(body.get("district")),
            city=body["city"],
            state=str(body["state"]).strip(),
            country=str(body["country"]).strip().upper(),
        )
        promote_verified_owner(user)
        db.add(user)
        db.commit()
        return create_test_session_token(
            clerk_user_id=clerk_id,
            email=user.email,
            email_verified=True,
        )
    finally:
        db.close()


def mint_guest(client) -> str:
    """Convidado isolado, no mesmo formato de antes, com Bearer de teste."""
    uid = uuid.uuid4()
    email = f"guest-{uid}@storyrus.app"
    clerk_id = f"user_{uid.hex}"
    db = _db(client)
    try:
        user = User(
            email=email,
            password_hash="!guest",
            clerk_user_id=clerk_id,
            credits=0,
            email_verified_at=datetime.now(UTC),
        )
        db.add(user)
        db.commit()
        return create_test_session_token(
            clerk_user_id=clerk_id,
            email=email,
            email_verified=True,
        )
    finally:
        db.close()


@pytest.fixture()
def auth_client(client):
    """Cliente com conta registrada e e-mail verificado."""
    token = signup_and_verify(client, "auth@example.com")
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture()
def guest_client(client):
    token = mint_guest(client)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
