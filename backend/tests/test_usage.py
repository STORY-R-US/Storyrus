"""API do painel de gastos: senha e agregacao de cost_usd."""

from datetime import UTC, datetime

import pytest

from app.config import settings
from app.database import get_db
from app.models import Asset, Job, JobStatus, OrderTicket, PrintOrder, Project, UsageEvent, User


def _session(client):
    gen = client.app.dependency_overrides[get_db]()
    return next(gen)


def _seed_job(client, *, cost_usd, job_type="EBOOK", child="Matteo"):
    db = _session(client)
    try:
        user = db.query(User).first()
        if user is None:
            user = User(email="u@t.com", password_hash="x", credits=10)
            db.add(user)
            db.flush()
        project = Project(user_id=user.id, status="EBOOK_READY", child_name=child)
        db.add(project)
        db.flush()
        job = Job(
            project_id=project.id,
            type=job_type,
            status=JobStatus.DONE.value,
            provider="nano-banana",
            cost_usd=cost_usd,
            cost_credits=1,
            created_at=datetime.now(UTC),
        )
        db.add(job)
        db.commit()
        return project.id
    finally:
        db.close()


def test_usage_without_password_still_rejects_anonymous(client, monkeypatch):
    """Sem senha compartilhada o painel segue aberto para a conta do dono."""
    monkeypatch.setattr(settings, "usage_dashboard_password", None)
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    monkeypatch.setattr(settings, "owner_emails", "")
    r = client.get("/v1/usage")
    assert r.status_code == 401


def test_usage_wrong_password_is_401(client, monkeypatch):
    monkeypatch.setattr(settings, "usage_dashboard_password", "segredo")
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    monkeypatch.setattr(settings, "usage_lockout_max_attempts", 10)
    r = client.get("/v1/usage", headers={"X-Usage-Password": "errada"})
    assert r.status_code == 401


def test_usage_accepts_previous_password_during_rotation(client, monkeypatch):
    monkeypatch.setattr(settings, "usage_dashboard_password", "nova")
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", "antiga")
    monkeypatch.setattr(settings, "usage_lockout_max_attempts", 10)
    r = client.get("/v1/usage", headers={"X-Usage-Password": "antiga"})
    assert r.status_code == 200, r.text


def test_usage_lockout_after_failed_attempts(client, monkeypatch):
    from app import rate_limit

    monkeypatch.setattr(settings, "usage_dashboard_password", "segredo")
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    monkeypatch.setattr(settings, "usage_lockout_max_attempts", 3)
    monkeypatch.setattr(settings, "usage_lockout_window_s", 900)
    rate_limit.reset()

    for _ in range(3):
        r = client.get("/v1/usage", headers={"X-Usage-Password": "errada"})
        assert r.status_code in (401, 429)
    locked = client.get("/v1/usage", headers={"X-Usage-Password": "errada"})
    assert locked.status_code == 429
    # Senha correta libera mesmo durante o lockout.
    still = client.get("/v1/usage", headers={"X-Usage-Password": "segredo"})
    assert still.status_code == 200, still.text


def test_usage_owner_jwt_bypasses_password(auth_client, monkeypatch):
    from app import rate_limit
    from app.database import get_db
    from app.models import User

    monkeypatch.setattr(settings, "usage_dashboard_password", "segredo")
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    monkeypatch.setattr(settings, "owner_emails", "auth@example.com")
    rate_limit.reset()

    gen = auth_client.app.dependency_overrides[get_db]()
    db = next(gen)
    try:
        user = db.query(User).filter(User.email == "auth@example.com").first()
        assert user is not None
        from datetime import UTC, datetime

        if user.email_verified_at is None:
            user.email_verified_at = datetime.now(UTC)
            db.add(user)
            db.commit()
    finally:
        db.close()

    ok = auth_client.get("/v1/usage")
    assert ok.status_code == 200, ok.text


def test_usage_owner_jwt_rejects_non_owner(auth_client, monkeypatch):
    from app import rate_limit

    monkeypatch.setattr(settings, "usage_dashboard_password", "segredo")
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    monkeypatch.setattr(settings, "owner_emails", "dono@storyrus.ai")
    rate_limit.reset()

    r = auth_client.get("/v1/usage")
    assert r.status_code == 401


def test_usage_success_clears_lockout_counter(client, monkeypatch):
    from app import rate_limit

    monkeypatch.setattr(settings, "usage_dashboard_password", "segredo")
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    monkeypatch.setattr(settings, "usage_lockout_max_attempts", 3)
    monkeypatch.setattr(settings, "usage_lockout_window_s", 900)
    rate_limit.reset()

    assert client.get("/v1/usage", headers={"X-Usage-Password": "errada"}).status_code == 401
    assert client.get("/v1/usage", headers={"X-Usage-Password": "errada"}).status_code == 401
    ok = client.get("/v1/usage", headers={"X-Usage-Password": "segredo"})
    assert ok.status_code == 200, ok.text
    # Contador zerado: mais 2 falhas nao devem lockar ainda.
    assert client.get("/v1/usage", headers={"X-Usage-Password": "errada"}).status_code == 401
    assert client.get("/v1/usage", headers={"X-Usage-Password": "errada"}).status_code == 401
    assert client.get("/v1/usage", headers={"X-Usage-Password": "segredo"}).status_code == 200


def test_usage_sums_seeded_jobs(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "usage_dashboard_password", "segredo")
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    _seed_job(auth_client, cost_usd=1.25, job_type="EBOOK")
    _seed_job(auth_client, cost_usd=0.25, job_type="STORY")
    _seed_job(auth_client, cost_usd=None, job_type="AVATAR")

    r = auth_client.get("/v1/usage", headers={"X-Usage-Password": "segredo"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["today_usd"] == 1.5
    assert body["month_usd"] == 1.5
    assert body["books_count"] == 3
    types = {b["key"]: b["usd"] for b in body["by_type"]}
    assert types["EBOOK"] == 1.25
    assert types["STORY"] == 0.25
    assert "AVATAR" not in types
    unmeasured = [b for b in body["books"] if b["usd"] is None]
    assert len(unmeasured) == 1
    # jobs com custo e sem usage_events viram linha "sem extrato"
    labels = [e["label"] for e in body["events"]]
    assert any("sem extrato" in lb for lb in labels)
    assert body["events_count"] >= 2


def test_usage_lists_named_image_events(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "usage_dashboard_password", "segredo")
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    project_id = _seed_job(auth_client, cost_usd=0.078, job_type="EBOOK")
    db = _session(auth_client)
    try:
        job = db.query(Job).filter(Job.project_id == project_id).first()
        db.add(
            UsageEvent(
                job_id=job.id,
                project_id=project_id,
                kind="image",
                provider="gemini",
                action="generate_scene",
                label="Página 1 — geração",
                cost_usd=0.039,
            )
        )
        db.add(
            UsageEvent(
                job_id=job.id,
                project_id=project_id,
                kind="image",
                provider="gemini",
                action="refine_scene",
                label="Página 1 — refine",
                cost_usd=0.039,
            )
        )
        db.commit()
    finally:
        db.close()

    r = auth_client.get("/v1/usage", headers={"X-Usage-Password": "segredo"})
    assert r.status_code == 200, r.text
    labels = [e["label"] for e in r.json()["events"]]
    assert "Página 1 — geração" in labels
    assert "Página 1 — refine" in labels
    assert not any("sem extrato" in lb for lb in labels)


def test_orders_scope_skips_spend_scan_and_print_files(auth_client, monkeypatch):
    """Listar Pedidos não pode ler imagens nem varrer os jobs de gasto."""
    monkeypatch.setattr(settings, "usage_dashboard_password", "segredo")
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    calls = {"prepare": 0, "bytes": 0}

    def _prepare(*_args, **_kwargs):
        calls["prepare"] += 1

    def _bytes(*_args, **_kwargs):
        calls["bytes"] += 1
        return b""

    monkeypatch.setattr("app.printkit.service.prepare_files", _prepare)
    monkeypatch.setattr("app.storage.get_bytes", _bytes)

    db = _session(auth_client)
    try:
        user = db.query(User).filter(User.email == "auth@example.com").one()
        project = Project(
            user_id=user.id,
            status="EBOOK_READY",
            child_name="Lia",
            book_size="M",
            cover_type="soft",
        )
        db.add(project)
        db.flush()
        db.add(Asset(project_id=project.id, kind="photo", storage_key="photos/lia.jpg"))
        db.add(
            Asset(
                project_id=project.id,
                kind="page_image",
                storage_key="pages/1.png",
                meta={"page": 1},
            )
        )
        db.commit()
        project_id = project.id
    finally:
        db.close()

    scoped = auth_client.get(
        "/v1/usage?scope=orders",
        headers={"X-Usage-Password": "segredo"},
    )
    assert scoped.status_code == 200, scoped.text
    assert scoped.headers["cache-control"] == "private, no-store"
    body = scoped.json()
    assert body["today_usd"] == 0
    assert body["events"] == []
    assert body["recent_jobs"] == []
    assert len(body["orders"]) == 1
    assert body["orders"][0]["print_code"].startswith("SR-")
    assert calls == {"prepare": 0, "bytes": 0}

    db = _session(auth_client)
    try:
        printed = db.query(PrintOrder).filter(PrintOrder.project_id == project_id).one()
        printed.status = "awaiting_pages"
        db.add(printed)
        db.commit()
    finally:
        db.close()

    again = auth_client.get("/v1/usage?scope=orders", headers={"X-Usage-Password": "segredo"})
    full = auth_client.get("/v1/usage", headers={"X-Usage-Password": "segredo"})
    assert again.status_code == 200, again.text
    assert full.status_code == 200, full.text
    assert full.headers["cache-control"] == "private, no-store"
    assert calls == {"prepare": 0, "bytes": 0}


def test_orders_scope_survives_bad_page_meta_and_service_order(auth_client, monkeypatch):
    """Metadado que não é dict, e falha ao abrir a OS, não podem responder 500."""
    monkeypatch.setattr(settings, "usage_dashboard_password", "segredo")
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)

    def _boom(*_args, **_kwargs):
        raise RuntimeError("os indisponivel")

    monkeypatch.setattr("app.routers.usage.attach_service_orders", _boom)
    monkeypatch.setattr("app.routers.usage.backfill_order_tickets", _boom)

    db = _session(auth_client)
    try:
        user = db.query(User).filter(User.email == "auth@example.com").one()
        project = Project(
            user_id=user.id,
            status="EBOOK_READY",
            child_name="Lia",
            story_text="Era uma vez.",
        )
        db.add(project)
        db.flush()
        db.add(OrderTicket(project_id=project.id, summary="Lia\nCriança: Lia"))
        db.add(
            Asset(
                project_id=project.id,
                kind="page_image",
                storage_key="pages/1.png",
                meta=["sem pagina"],
            )
        )
        db.commit()
    finally:
        db.close()

    scoped = auth_client.get(
        "/v1/usage?scope=orders",
        headers={"X-Usage-Password": "segredo"},
    )
    assert scoped.status_code == 200, scoped.text
    body = scoped.json()
    assert len(body["orders"]) == 1
    assert body["orders"][0]["has_story"] is True
    assert body["orders"][0]["summary"].startswith("Lia")


def test_owner_edits_the_order(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "usage_dashboard_password", "segredo")
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    db = _session(auth_client)
    try:
        user = db.query(User).filter(User.email == "auth@example.com").one()
        project = Project(
            user_id=user.id,
            status="EBOOK_READY",
            child_name="Lia",
            child_age=4,
            book_size="M",
            cover_type="soft",
        )
        db.add(project)
        db.flush()
        ticket = OrderTicket(project_id=project.id, summary="NOVO LIVRO\nNome: Lia")
        db.add(ticket)
        db.add(
            PrintOrder(
                project_id=project.id,
                code="SR-EDIT01",
                status="awaiting_spec",
                payment_status="unpaid",
                quantity=1,
                recipient_name="Ana",
                street="Rua Velha",
                number="1",
                district="Centro",
                city="São Paulo",
                state="SP",
                postal_code="01310100",
            )
        )
        db.commit()
        ticket_id = str(ticket.id)
    finally:
        db.close()

    edited = auth_client.patch(
        f"/v1/usage/orders/{ticket_id}",
        headers={"X-Usage-Password": "segredo"},
        json={
            "child_name": "Lorena",
            "child_age": 8,
            "dedication": "Com carinho",
            "book_size": "P",
            "cover_type": "hard",
            "quantity": 2,
            "payment_status": "paid",
            "street": "Rua Nova",
            "tracking_code": "BR123",
        },
    )
    assert edited.status_code == 200, edited.text
    body = edited.json()
    assert body["child_name"] == "Lorena"
    assert body["child_age"] == 8
    assert body["dedication"] == "Com carinho"
    assert body["book_size"] == "P"
    assert body["cover_type"] == "hard"
    assert body["quantity"] == 2
    assert body["payment_status"] == "paid"
    assert body["street"] == "Rua Nova"
    assert body["tracking_code"] == "BR123"
    assert "Nome: Lorena" in body["summary"]
    assert "Dedicatória: Com carinho" in body["summary"]


def test_delete_order_apaga_o_pedido_e_o_projeto(auth_client, monkeypatch):
    """Excluir o pedido remove o projeto (fotos, arquivos, OS) e não recria."""
    monkeypatch.setattr(settings, "usage_dashboard_password", "segredo")
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)

    db = _session(auth_client)
    try:
        user = db.query(User).filter(User.email == "auth@example.com").one()
        project = Project(user_id=user.id, status="EBOOK_READY", child_name="Lia")
        db.add(project)
        db.flush()
        ticket = OrderTicket(project_id=project.id, summary="Lia\nCriança: Lia")
        db.add(ticket)
        db.add(Asset(project_id=project.id, kind="photo", storage_key="photos/lia.jpg"))
        db.add(
            PrintOrder(
                project_id=project.id,
                code="SR-DEL001",
                status="awaiting_spec",
                payment_status="unpaid",
            )
        )
        db.commit()
        ticket_id = ticket.id
        project_id = project.id
    finally:
        db.close()

    sem_senha = auth_client.delete(f"/v1/usage/orders/{ticket_id}")
    assert sem_senha.status_code == 401

    done = auth_client.delete(
        f"/v1/usage/orders/{ticket_id}",
        headers={"X-Usage-Password": "segredo"},
    )
    assert done.status_code == 204, done.text

    db = _session(auth_client)
    try:
        assert db.query(OrderTicket).filter(OrderTicket.id == ticket_id).first() is None
        assert db.query(Project).filter(Project.id == project_id).first() is None
        assert db.query(Asset).filter(Asset.project_id == project_id).count() == 0
        assert db.query(PrintOrder).filter(PrintOrder.project_id == project_id).count() == 0
    finally:
        db.close()

    # A foto foi junto: o painel não recria o pedido no próximo carregamento.
    listed = auth_client.get("/v1/usage?scope=orders", headers={"X-Usage-Password": "segredo"})
    assert listed.status_code == 200, listed.text
    assert listed.json()["orders"] == []


def test_delete_order_desconhecido_responde_404(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "usage_dashboard_password", "segredo")
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)

    import uuid as _uuid

    miss = auth_client.delete(
        f"/v1/usage/orders/{_uuid.uuid4()}",
        headers={"X-Usage-Password": "segredo"},
    )
    assert miss.status_code == 404


def test_delete_order_apaga_tudo_com_fk_enforcada():
    """Com FK enforcada (como no Postgres), a exclusao apaga todos os filhos.

    O SQLite dos testes desliga FK por padrao, entao um filho esquecido passaria
    batido aqui e so quebraria em producao. Aqui ligamos `PRAGMA foreign_keys`.
    """
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.database import Base
    from app.routers.usage import delete_order

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _record):  # noqa: ANN001
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        user = User(email="fk@example.com", password_hash="x", credits=1)
        db.add(user)
        db.flush()
        project = Project(user_id=user.id, status="EBOOK_READY", child_name="Lia")
        db.add(project)
        db.flush()
        ticket = OrderTicket(project_id=project.id, summary="Lia")
        db.add(ticket)
        db.add(Asset(project_id=project.id, kind="photo", storage_key="photos/lia.jpg"))
        db.add(PrintOrder(project_id=project.id, code="SR-FK001"))
        job = Job(project_id=project.id, type="EBOOK", status=JobStatus.DONE.value)
        db.add(job)
        db.flush()
        db.add(
            UsageEvent(
                project_id=project.id,
                job_id=job.id,
                action="ebook",
                label="Lia",
            )
        )
        db.commit()
        ticket_id = ticket.id
        project_id = project.id

        resp = delete_order(ticket_id, None, db)
        assert resp.status_code == 204

        assert db.get(Project, project_id) is None
        assert db.query(OrderTicket).filter_by(project_id=project_id).count() == 0
        assert db.query(Asset).filter_by(project_id=project_id).count() == 0
        assert db.query(PrintOrder).filter_by(project_id=project_id).count() == 0
        assert db.query(Job).filter_by(project_id=project_id).count() == 0
        assert db.query(UsageEvent).filter_by(project_id=project_id).count() == 0
    finally:
        db.close()


def test_delete_drafts_removes_projects_and_guest_accounts():
    """Rascunhos e contas de visita saem. Conta cadastrada permanece."""
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.database import Base
    from app.models import UserVoice
    from app.routers.usage import delete_drafts

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _record):  # noqa: ANN001
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        owner = User(
            email="owner@storyrus.ai",
            password_hash="real",
            credits=1,
            is_admin=True,
            email_verified_at=datetime.now(UTC),
        )
        guest = User(email="visitante@storyrus.app", password_hash="!guest", credits=0)
        debug = User(email="storyrus-debug@example.com", password_hash="x", credits=0)
        db.add_all([owner, guest, debug])
        db.flush()
        db.add(UserVoice(user_id=guest.id, name="Voz", elevenlabs_voice_id="v", sample_storage_key="a"))
        own = Project(user_id=owner.id, status="CREATED", child_name="Lia")
        theirs = Project(user_id=guest.id, status="CREATED", child_name="Bia")
        db.add_all([own, theirs])
        db.flush()
        db.add(Asset(project_id=own.id, kind="photo", storage_key="photos/lia.jpg"))
        job = Job(project_id=theirs.id, type="EBOOK", status=JobStatus.FAILED.value)
        db.add(job)
        db.flush()
        db.add(UsageEvent(project_id=theirs.id, job_id=job.id, action="ebook", label="Bia"))
        db.commit()

        result = delete_drafts(None, db)
        assert result == {"projects_removed": 2, "accounts_removed": 2}
        assert db.query(Project).count() == 0
        assert db.query(Asset).count() == 0
        assert db.query(Job).count() == 0
        assert db.query(UsageEvent).count() == 0
        assert db.query(UserVoice).count() == 0
        left = {user.email for user in db.query(User).all()}
        assert left == {"owner@storyrus.ai"}
    finally:
        db.close()


def test_my_orders_lists_only_the_accounts_tickets(auth_client):
    """A tela "Meus Pedidos" do cliente nunca mostra pedido de outra conta."""
    db = _session(auth_client)
    try:
        me = db.query(User).filter(User.email == "auth@example.com").one()
        other = User(email="other@example.com", password_hash="x", credits=0)
        db.add(other)
        db.flush()
        mine = Project(user_id=me.id, status="EBOOK_READY", child_name="Lia")
        theirs = Project(user_id=other.id, status="EBOOK_READY", child_name="Bia")
        db.add_all([mine, theirs])
        db.flush()
        db.add(OrderTicket(project_id=mine.id, summary="Meu\nCriança: Lia"))
        db.add(OrderTicket(project_id=theirs.id, summary="Deles\nCriança: Bia"))
        db.commit()
    finally:
        db.close()

    r = auth_client.get("/v1/usage/orders/mine")
    assert r.status_code == 200, r.text
    assert r.headers["cache-control"] == "private, no-store"
    body = r.json()
    assert len(body) == 1
    assert "Lia" in body[0]["summary"]
    assert body[0]["mine"] is False
    assert body[0]["account_email"] == "auth@example.com"


def test_my_orders_requires_a_session(client):
    assert client.get("/v1/usage/orders/mine").status_code == 401


def test_my_orders_recovers_missing_ticket_only_for_current_account(auth_client, monkeypatch):
    monkeypatch.setattr(
        "app.storage.get_bytes", lambda *args: pytest.fail("Listing must not read images")
    )
    db = _session(auth_client)
    try:
        me = db.query(User).filter(User.email == "auth@example.com").one()
        other = User(email="other@example.com", password_hash="x", credits=0)
        db.add(other)
        db.flush()
        mine = Project(user_id=me.id, child_name="Lia")
        theirs = Project(user_id=other.id, child_name="Bia")
        db.add_all([mine, theirs])
        db.flush()
        db.add_all(
            [
                Asset(project_id=mine.id, kind="photo", storage_key="mine.jpg"),
                Asset(project_id=theirs.id, kind="photo", storage_key="other.jpg"),
            ]
        )
        db.commit()
        mine_id, other_id = mine.id, theirs.id
        r = auth_client.get("/v1/usage/orders/mine")
        assert r.status_code == 200, r.text
        assert [row["project_id"] for row in r.json()] == [str(mine_id)]
        assert db.query(OrderTicket).filter_by(project_id=other_id).count() == 0
        again = auth_client.get("/v1/usage/orders/mine")
        assert [row["id"] for row in again.json()] == [row["id"] for row in r.json()]
    finally:
        db.close()
