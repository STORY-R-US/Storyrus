"""Troca da instância do Clerk (dev → produção) sem perder contas nem livros."""

import uuid
from datetime import UTC, datetime

import httpx
import pytest

from app.config import settings
from app.database import get_db
from app.models import ClerkAccountMap, Project, User
from app.services import clerk_cutover
from app.services.clerk_identity import create_test_session_token

LIVE_KEY = "sk_live_suite_prod"
DEV_KEY = "sk_test_suite_dev"


def _db(client):
    return next(client.app.dependency_overrides[get_db]())


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _user(
    client,
    email: str,
    *,
    verified: bool = True,
    dev_id: str | None = "auto",
    admin: bool = False,
    credits: int = 5,
) -> tuple[uuid.UUID, str | None]:
    db = _db(client)
    try:
        clerk_id = f"user_dev_{uuid.uuid4().hex[:12]}" if dev_id == "auto" else dev_id
        now = datetime.now(UTC)
        user = User(
            email=email,
            password_hash="!clerk",
            clerk_user_id=clerk_id,
            credits=credits,
            is_admin=admin,
            email_verified_at=now if verified else None,
            terms_accepted_at=now,
            adult_confirmed_at=now,
        )
        db.add(user)
        db.commit()
        db.add(Project(user_id=user.id, status="CREATED", child_name="Lia"))
        db.commit()
        return user.id, clerk_id
    finally:
        db.close()


def _token(clerk_id: str, email: str, verified: bool = True) -> str:
    return create_test_session_token(clerk_user_id=clerk_id, email=email, email_verified=verified)


class FakeClerk:
    """Instância de produção do Clerk em memória (GET/POST/DELETE /users)."""

    def __init__(self) -> None:
        self.users: list[dict] = []
        self.calls: list[tuple[str, str]] = []
        self.fail_with: int | None = None

    def add(self, email: str, external_id: str | None) -> str:
        uid = f"user_prod_{uuid.uuid4().hex[:12]}"
        self.users.append(
            {"id": uid, "external_id": external_id, "email_addresses": [{"email_address": email}]}
        )
        return uid

    def __call__(self, method, path, *, params=None, payload=None):
        self.calls.append((method, path))
        request = httpx.Request(method, f"https://api.clerk.com/v1{path}")
        if self.fail_with:
            return httpx.Response(self.fail_with, json={}, request=request)
        if method == "GET" and path == "/users":
            wanted = set((params or {}).get("email_address") or [])
            found = [
                u
                for u in self.users
                if any(e["email_address"] in wanted for e in u["email_addresses"])
            ]
            return httpx.Response(200, json=found, request=request)
        if method == "POST" and path == "/users":
            uid = self.add(payload["email_address"][0], payload.get("external_id"))
            assert payload["skip_password_requirement"] is True
            return httpx.Response(200, json={"id": uid}, request=request)
        if method == "DELETE":
            self.users = [u for u in self.users if path != f"/users/{u['id']}"]
            return httpx.Response(200, json={}, request=request)
        return httpx.Response(404, json={}, request=request)


@pytest.fixture
def fake_clerk(monkeypatch):
    fake = FakeClerk()
    monkeypatch.setattr(clerk_cutover, "_request", fake)
    monkeypatch.setattr(clerk_cutover.time, "sleep", lambda _s: None)
    monkeypatch.setattr(settings, "clerk_secret_key", DEV_KEY)
    monkeypatch.setattr(settings, "clerk_production_secret_key", LIVE_KEY)
    return fake


@pytest.fixture
def admin(client):
    _uid, dev_id = _user(client, "dona@storyrus.ai", admin=True)
    return _auth(_token(dev_id, "dona@storyrus.ai"))


def _row(client, user_id) -> ClerkAccountMap | None:
    db = _db(client)
    try:
        from sqlalchemy import select

        return db.scalar(select(ClerkAccountMap).where(ClerkAccountMap.user_id == user_id))
    finally:
        db.close()


def _clerk_id(client, user_id) -> str | None:
    db = _db(client)
    try:
        return db.get(User, user_id).clerk_user_id
    finally:
        db.close()


def test_rotas_so_para_admin(client, fake_clerk):
    _uid, dev_id = _user(client, "mae@familia-exemplo.com.br")
    comum = _auth(_token(dev_id, "mae@familia-exemplo.com.br"))
    assert client.get("/v1/admin/clerk-cutover", headers=comum).status_code == 401
    assert client.post("/v1/admin/clerk-cutover/stage", headers=comum).status_code == 401
    assert client.get("/v1/admin/clerk-cutover").status_code == 401


def test_plano_conta_sem_chamar_o_clerk(client, fake_clerk, admin):
    _user(client, "mae@familia-exemplo.com.br")
    _user(client, "pai@familia-exemplo.com.br", verified=False)
    _user(client, "sem-login@familia-exemplo.com.br", verified=False, dev_id=None)
    _user(client, "robo@example.com")
    body = client.get("/v1/admin/clerk-cutover", headers=admin).json()
    assert body["to_create"] == 2  # mãe + dona (admin)
    assert body["to_mark_pending_email"] == 1
    assert body["unverified_without_login"] == 1
    assert body["skipped_test_or_guest"] >= 1
    assert body["production_key_ready"] is True
    assert body["live_instance"] is False
    assert fake_clerk.calls == []


def test_preparo_exige_chave_de_producao(client, fake_clerk, admin, monkeypatch):
    monkeypatch.setattr(settings, "clerk_production_secret_key", "sk_test_errada")
    response = client.post("/v1/admin/clerk-cutover/stage", headers=admin)
    assert response.status_code == 409
    assert "sk_live_" in response.json()["detail"]


def test_preparo_cria_na_producao_sem_mexer_no_login_atual(client, fake_clerk, admin):
    uid, dev_id = _user(client, "mae@familia-exemplo.com.br")
    pend_uid, _ = _user(client, "pai@familia-exemplo.com.br", verified=False)
    body = client.post("/v1/admin/clerk-cutover/stage", headers=admin).json()
    assert body["result"] == {"staged": 2, "pending_email": 1}
    assert body["remaining"] == 0

    row = _row(client, uid)
    assert row.status == "staged"
    assert row.dev_clerk_user_id == dev_id
    prod = next(u for u in fake_clerk.users if u["id"] == row.prod_clerk_user_id)
    assert prod["external_id"] == str(uid)
    assert _row(client, pend_uid).status == "pending_email"
    # Login de hoje continua igual.
    assert _clerk_id(client, uid) == dev_id
    me = client.get("/v1/auth/me", headers=_auth(_token(dev_id, "mae@familia-exemplo.com.br")))
    assert me.status_code == 200 and me.json()["id"] == str(uid)

    # Repetir não cria de novo.
    again = client.post("/v1/admin/clerk-cutover/stage", headers=admin).json()
    assert again["processed"] == 0
    assert len(fake_clerk.users) == 2


def test_reaproveita_conta_de_producao_com_o_mesmo_external_id(client, fake_clerk, admin):
    uid, _ = _user(client, "mae@familia-exemplo.com.br")
    existing = fake_clerk.add("mae@familia-exemplo.com.br", str(uid))
    client.post("/v1/admin/clerk-cutover/stage", headers=admin)
    assert _row(client, uid).prod_clerk_user_id == existing
    assert sum(1 for m, _p in fake_clerk.calls if m == "POST") == 1  # só a da dona


def test_conflito_nao_liga_e_fica_para_conferir(client, fake_clerk, admin):
    uid, _ = _user(client, "mae@familia-exemplo.com.br")
    fake_clerk.add("mae@familia-exemplo.com.br", None)
    client.post("/v1/admin/clerk-cutover/stage", headers=admin)
    row = _row(client, uid)
    assert row.status == "conflict" and row.prod_clerk_user_id is None
    plan = client.get("/v1/admin/clerk-cutover", headers=admin).json()
    assert plan["by_status"]["conflict"] == 1
    assert plan["conflicts"][0]["email"] == "ma***@familia-exemplo.com.br"
    assert plan["to_create"] == 0
    # Sem o pedido explícito, o conflito não volta a ser tentado.
    again = client.post("/v1/admin/clerk-cutover/stage", headers=admin).json()
    assert again["processed"] == 0


def test_limite_de_taxa_para_o_lote(client, fake_clerk, admin):
    _user(client, "mae@familia-exemplo.com.br")
    fake_clerk.fail_with = 429
    body = client.post("/v1/admin/clerk-cutover/stage", headers=admin).json()
    assert body["rate_limited"] is True
    assert body["remaining"] == 2


def test_primeiro_login_na_producao_assume_a_mesma_conta(client, fake_clerk, admin, monkeypatch):
    uid, dev_id = _user(client, "mae@familia-exemplo.com.br", credits=33)
    client.post("/v1/admin/clerk-cutover/stage", headers=admin)
    prod_id = _row(client, uid).prod_clerk_user_id

    # Antes da troca das chaves, o id de produção não assume nada.
    early = client.get("/v1/auth/me", headers=_auth(_token(prod_id, "mae@familia-exemplo.com.br")))
    assert early.status_code == 409
    assert _clerk_id(client, uid) == dev_id

    monkeypatch.setattr(settings, "clerk_secret_key", LIVE_KEY)
    me = client.get("/v1/auth/me", headers=_auth(_token(prod_id, "mae@familia-exemplo.com.br")))
    assert me.status_code == 200, me.text
    assert me.json()["id"] == str(uid)
    assert me.json()["credits"] == 33
    projects = client.get(
        "/v1/projects", headers=_auth(_token(prod_id, "mae@familia-exemplo.com.br"))
    )
    assert len(projects.json()) == 1
    row = _row(client, uid)
    assert row.status == "active" and row.activated_at is not None
    assert _clerk_id(client, uid) == prod_id
    # O id antigo não entra mais.
    old = client.get("/v1/auth/me", headers=_auth(_token(dev_id, "mae@familia-exemplo.com.br")))
    assert old.status_code == 409


def test_admin_entra_no_painel_logo_depois_da_troca(client, fake_clerk, admin, monkeypatch):
    client.post("/v1/admin/clerk-cutover/stage", headers=admin)
    db = _db(client)
    try:
        from sqlalchemy import select

        dona = db.scalar(select(User).where(User.email == "dona@storyrus.ai"))
        dona_id = dona.id
    finally:
        db.close()
    prod_id = _row(client, dona_id).prod_clerk_user_id
    monkeypatch.setattr(settings, "clerk_secret_key", LIVE_KEY)
    painel = client.get(
        "/v1/admin/clerk-cutover", headers=_auth(_token(prod_id, "dona@storyrus.ai"))
    )
    assert painel.status_code == 200
    assert painel.json()["live_instance"] is True


def test_conta_sem_email_verificado_so_religa_com_email_verificado(
    client, fake_clerk, admin, monkeypatch
):
    uid, _dev = _user(client, "pai@familia-exemplo.com.br", verified=False)
    client.post("/v1/admin/clerk-cutover/stage", headers=admin)
    monkeypatch.setattr(settings, "clerk_secret_key", LIVE_KEY)
    novo = "user_prod_novo_pai"
    nao = client.get(
        "/v1/auth/me", headers=_auth(_token(novo, "pai@familia-exemplo.com.br", False))
    )
    assert nao.status_code != 200
    sim = client.get("/v1/auth/me", headers=_auth(_token(novo, "pai@familia-exemplo.com.br", True)))
    assert sim.status_code == 200, sim.text
    assert sim.json()["id"] == str(uid)
    assert _row(client, uid).status == "active_email"


def test_conta_ja_ligada_nao_religa_por_email(client, fake_clerk, admin, monkeypatch):
    uid, dev_id = _user(client, "mae@familia-exemplo.com.br")
    client.post("/v1/admin/clerk-cutover/stage", headers=admin)
    monkeypatch.setattr(settings, "clerk_secret_key", LIVE_KEY)
    # Outra conta de produção com o mesmo e-mail, fora do mapa.
    intrusa = client.get(
        "/v1/auth/me", headers=_auth(_token("user_prod_intrusa", "mae@familia-exemplo.com.br"))
    )
    assert intrusa.status_code == 409
    assert _clerk_id(client, uid) == dev_id


def test_voltar_devolve_os_ids_antigos(client, fake_clerk, admin, monkeypatch):
    uid, dev_id = _user(client, "mae@familia-exemplo.com.br")
    client.post("/v1/admin/clerk-cutover/stage", headers=admin)
    prod_id = _row(client, uid).prod_clerk_user_id
    monkeypatch.setattr(settings, "clerk_secret_key", LIVE_KEY)
    client.get("/v1/auth/me", headers=_auth(_token(prod_id, "mae@familia-exemplo.com.br")))
    db = _db(client)
    try:
        from sqlalchemy import select

        dona = db.scalar(select(User).where(User.email == "dona@storyrus.ai"))
        dona_prod = _row(client, dona.id).prod_clerk_user_id
    finally:
        db.close()
    admin_live = _auth(_token(dona_prod, "dona@storyrus.ai"))

    sem_confirmar = client.post(
        "/v1/admin/clerk-cutover/rollback", headers=admin_live, json={"confirm": "sim"}
    )
    assert sem_confirmar.status_code == 400
    body = client.post(
        "/v1/admin/clerk-cutover/rollback", headers=admin_live, json={"confirm": "VOLTAR"}
    ).json()
    assert body["restored"] == 2
    assert _clerk_id(client, uid) == dev_id
    assert _row(client, uid).status == "rolled_back"
    # Com a chave de produção ainda no ar, o login de produção não reassume.
    again = client.get("/v1/auth/me", headers=_auth(_token(prod_id, "mae@familia-exemplo.com.br")))
    assert again.status_code == 409
    assert _clerk_id(client, uid) == dev_id

    monkeypatch.setattr(settings, "clerk_secret_key", DEV_KEY)
    me = client.get("/v1/auth/me", headers=_auth(_token(dev_id, "mae@familia-exemplo.com.br")))
    assert me.status_code == 200 and me.json()["id"] == str(uid)


def test_apagar_conta_remove_o_mapa(client, fake_clerk, admin):
    uid, _dev = _user(client, "mae@familia-exemplo.com.br")
    client.post("/v1/admin/clerk-cutover/stage", headers=admin)
    assert _row(client, uid) is not None
    response = client.delete(f"/v1/users/{uid}", headers=admin)
    assert response.status_code == 204, response.text
    assert _row(client, uid) is None


def test_novo_preparo_depois_de_voltar_reaproveita_a_conta(client, fake_clerk, admin, monkeypatch):
    uid, _dev = _user(client, "mae@familia-exemplo.com.br")
    client.post("/v1/admin/clerk-cutover/stage", headers=admin)
    prod_id = _row(client, uid).prod_clerk_user_id
    db = _db(client)
    try:
        row = db.get(ClerkAccountMap, _row(client, uid).id)
        row.status = "rolled_back"
        db.commit()
    finally:
        db.close()
    body = client.post("/v1/admin/clerk-cutover/stage", headers=admin).json()
    assert body["result"] == {"staged": 1}
    assert _row(client, uid).status == "staged"
    assert _row(client, uid).prod_clerk_user_id == prod_id
    assert len(fake_clerk.users) == 2
