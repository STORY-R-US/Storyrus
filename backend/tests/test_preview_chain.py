"""API + worker: cadeia automática de prévia (avatar → story → ebook trio OpenAI)."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai_clients.base import ImageResult, ProviderError
from app.config import settings
from app.database import Base
from app.models import (
    Asset,
    AssetKind,
    Job,
    JobStatus,
    JobType,
    PrintOrder,
    Project,
    ProjectStatus,
    User,
)
from app.services import preview_chain
from app.workers import handlers, runner
from tests.test_workers import FakeImage, FakeText


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    s = Session()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture()
def mem_storage(monkeypatch):
    store: dict[str, bytes] = {}
    monkeypatch.setattr("app.storage.put_bytes", lambda k, d, ct="x": store.setdefault(k, d) or k)
    monkeypatch.setattr("app.storage.get_bytes", lambda k: store.get(k, b"bytes"))
    monkeypatch.setattr(
        handlers.storage, "put_bytes", lambda k, d, ct="x": store.setdefault(k, d) or k
    )
    monkeypatch.setattr(handlers.storage, "get_bytes", lambda k: store.get(k, b"bytes"))
    return store


def _seed(db, status=ProjectStatus.CREATED, credits=10):
    u = User(email=f"{uuid.uuid4().hex}@t.com", password_hash="x", credits=credits)
    db.add(u)
    db.flush()
    p = Project(user_id=u.id, status=status.value, style="cartoon")
    db.add(p)
    db.flush()
    return u, p


def _job(db, project, jtype, cost=1, payload=None):
    j = Job(
        project_id=project.id,
        type=jtype,
        status=JobStatus.PENDING.value,
        cost_credits=cost,
        result={"payload": payload} if payload else None,
    )
    db.add(j)
    db.commit()
    db.refresh(j)
    return j


def test_preview_requires_photo(auth_client):
    pid = auth_client.post("/v1/projects", json={"style": "cartoon"}).json()["id"]
    r = auth_client.post(f"/v1/projects/{pid}/preview", json={})
    assert r.status_code == 400
    assert "foto" in r.json()["detail"].lower()


def test_preview_enqueues_avatar_with_chain_flag(auth_client):
    pid = auth_client.post("/v1/projects", json={"style": "cartoon"}).json()["id"]
    assert (
        auth_client.post(
            f"/v1/projects/{pid}/photos", json={"content_type": "image/jpeg", "ext": "jpg"}
        ).status_code
        == 201
    )
    before = auth_client.get("/v1/credits").json()["credits"]
    r = auth_client.post(
        f"/v1/projects/{pid}/preview",
        json={"brief": "aventura espacial com Lila"},
        headers={"Idempotency-Key": "preview-1"},
    )
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["type"] == "AVATAR"
    assert body["status"] == "PENDING"
    assert auth_client.get("/v1/credits").json()["credits"] == before

    jobs = auth_client.get(f"/v1/projects/{pid}/jobs").json()
    assert len(jobs) == 1
    assert jobs[0]["type"] == "AVATAR"
    assert jobs[0]["result"]["payload"]["preview_chain"] is True
    assert jobs[0]["result"]["payload"]["brief"] == "aventura espacial com Lila"

    # Mesma Idempotency-Key: o mesmo job, saldo intacto.
    r2 = auth_client.post(
        f"/v1/projects/{pid}/preview",
        json={"brief": "outro"},
        headers={"Idempotency-Key": "preview-1"},
    )
    assert r2.status_code == 202
    assert r2.json()["job_id"] == body["job_id"]
    assert auth_client.get("/v1/credits").json()["credits"] == before


def test_preview_conflict_while_active(auth_client):
    pid = auth_client.post("/v1/projects", json={"style": "cartoon"}).json()["id"]
    auth_client.post(
        f"/v1/projects/{pid}/photos", json={"content_type": "image/jpeg", "ext": "jpg"}
    )
    assert (
        auth_client.post(
            f"/v1/projects/{pid}/preview", headers={"Idempotency-Key": "a"}
        ).status_code
        == 202
    )
    r = auth_client.post(f"/v1/projects/{pid}/preview", headers={"Idempotency-Key": "b"})
    assert r.status_code == 409
    assert "andamento" in r.json()["detail"].lower()


def test_preview_starts_at_story_when_character_exists(auth_client):
    """Com character_ref já presente, a prévia começa em STORY."""
    from app.database import get_db
    from app.main import app
    from app.models import Project

    pid = auth_client.post("/v1/projects", json={"style": "cartoon"}).json()["id"]
    auth_client.post(
        f"/v1/projects/{pid}/photos", json={"content_type": "image/jpeg", "ext": "jpg"}
    )
    gen = app.dependency_overrides[get_db]()
    db = next(gen)
    try:
        p = db.get(Project, uuid.UUID(pid))
        assert p is not None
        p.character_ref = {"storage_key": "char1", "mime": "image/png"}
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    r = auth_client.post(
        f"/v1/projects/{pid}/preview",
        json={"brief": "brief do studio"},
        headers={"Idempotency-Key": "story-start"},
    )
    assert r.status_code == 202, r.text
    assert r.json()["type"] == "STORY"


def test_story_endpoint_accepts_brief(auth_client):
    pid = auth_client.post("/v1/projects", json={"style": "cartoon"}).json()["id"]
    auth_client.post(
        f"/v1/projects/{pid}/photos", json={"content_type": "image/jpeg", "ext": "jpg"}
    )
    r = auth_client.post(
        f"/v1/projects/{pid}/story",
        json={"brief": "herói corajoso"},
        headers={"Idempotency-Key": "s1"},
    )
    assert r.status_code == 202
    jobs = auth_client.get(f"/v1/projects/{pid}/jobs").json()
    assert jobs[0]["result"]["payload"]["brief"] == "herói corajoso"


@pytest.mark.asyncio
async def test_avatar_preview_chains_to_story(db, mem_storage, monkeypatch):
    monkeypatch.setattr(handlers, "get_image_provider", lambda *a, **k: FakeImage())
    u, p = _seed(db, credits=20)
    db.add(Asset(project_id=p.id, kind=AssetKind.PHOTO.value, storage_key="photo1"))
    db.commit()

    j = _job(db, p, "AVATAR", payload={"preview_chain": True, "brief": "espaço"})
    await runner.process_job(db, j)
    db.refresh(j)
    db.refresh(p)
    assert j.status == JobStatus.DONE.value
    assert p.character_ref
    assert p.character_approved_at is not None

    next_jobs = db.scalars(
        select(Job).where(Job.project_id == p.id, Job.type == JobType.STORY.value)
    ).all()
    assert len(next_jobs) == 1
    assert preview_chain.is_preview_chain(next_jobs[0])
    assert next_jobs[0].result["payload"]["brief"] == "espaço"
    assert next_jobs[0].status == JobStatus.PENDING.value
    db.refresh(u)
    assert u.credits == 20


@pytest.mark.asyncio
async def test_story_preview_chains_to_ebook(db, mem_storage, monkeypatch):
    monkeypatch.setattr(handlers, "get_text_provider", lambda *a, **k: FakeText())
    u, p = _seed(db, credits=20)
    p.character_ref = {"storage_key": "char1", "mime": "image/png"}
    db.commit()

    j = _job(db, p, "STORY", payload={"preview_chain": True, "brief": "x"})
    await runner.process_job(db, j)
    db.refresh(p)
    assert p.status == ProjectStatus.STORY_READY.value

    ebook = db.scalars(
        select(Job).where(Job.project_id == p.id, Job.type == JobType.EBOOK.value)
    ).all()
    assert len(ebook) == 1
    assert preview_chain.is_preview_chain(ebook[0])
    # Prévia não agenda storyboard (só serve ao vídeo).
    sb = db.scalars(
        select(Job).where(Job.project_id == p.id, Job.type == JobType.STORYBOARD.value)
    ).all()
    assert sb == []
    db.refresh(u)
    assert u.credits == 20


@pytest.mark.asyncio
async def test_ebook_preview_makes_openai_trio_without_video(db, mem_storage, monkeypatch):
    monkeypatch.setattr(handlers, "get_text_provider", lambda *a, **k: FakeText())
    monkeypatch.setattr(handlers, "get_image_provider", lambda *a, **k: FakeImage())
    monkeypatch.setattr("app.config.settings.offline_fallback", True)
    u, p = _seed(db, credits=20)
    p.character_ref = {"storage_key": "char1", "mime": "image/png"}
    p.story_text = (
        "Título: Teste\n\nPágina 1: Uma aventura.\n\nPágina 2: Continua.\n\nPágina 3: Fim."
    )
    p.character_approved_at = None
    db.commit()
    mem_storage["char1"] = b"CHAR"

    j = _job(db, p, "EBOOK", payload={"preview_chain": True})
    await runner.process_job(db, j)
    db.refresh(j)
    db.refresh(p)
    assert j.status == JobStatus.DONE.value
    assert p.status == ProjectStatus.EBOOK_READY.value
    assert p.book_approved_at is not None

    covers = db.scalars(
        select(Asset).where(Asset.project_id == p.id, Asset.kind == AssetKind.COVER.value)
    ).all()
    pages = db.scalars(
        select(Asset).where(Asset.project_id == p.id, Asset.kind == AssetKind.PAGE_IMAGE.value)
    ).all()
    hands = db.scalars(
        select(Asset).where(Asset.project_id == p.id, Asset.kind == AssetKind.IN_HAND.value)
    ).all()
    assert len(covers) == 1
    assert len(pages) == 1
    assert len(hands) == 1

    videos = db.scalars(
        select(Job).where(Job.project_id == p.id, Job.type == JobType.VIDEO.value)
    ).all()
    assert videos == []
    service_order = db.scalar(select(PrintOrder).where(PrintOrder.project_id == p.id))
    assert service_order is not None
    assert service_order.code.startswith("SR-")
    assert p.print_requested_at is None
    db.refresh(u)
    assert u.credits == 20  # EBOOK job já existia; não debitou VIDEO


def _capture_preview_email(monkeypatch) -> list[dict]:
    sent: list[dict] = []
    monkeypatch.setattr(
        "app.services.transactional_email.send_preview_ready_email",
        lambda **kwargs: sent.append(kwargs) or True,
    )
    return sent


def test_preview_ready_emails_the_client_once(db, monkeypatch):
    """Ao fim da prévia (história + imagens), o cliente recebe um e-mail — só uma vez."""
    u, p = _seed(db)
    p.child_name = "Lia"
    db.commit()
    sent = _capture_preview_email(monkeypatch)

    job = _job(db, p, "EBOOK", payload={"preview_chain": True})
    preview_chain.finalize_preview_ebook(db, p, job)
    db.refresh(p)
    assert len(sent) == 1
    assert sent[0]["to_email"] == u.email
    assert sent[0]["child_name"] == "Lia"
    assert p.preview_notified_at is not None

    # Re-finalizar (retry do job) não manda o aviso de novo.
    preview_chain.finalize_preview_ebook(db, p, job)
    assert len(sent) == 1


def test_preview_ready_skips_guest_accounts(db, monkeypatch):
    """Conta convidada (sentinela) não tem e-mail real: nenhum aviso é enviado."""
    u, p = _seed(db)
    u.email = "convidado@storyrus.app"
    u.password_hash = "!guest"
    db.commit()
    sent = _capture_preview_email(monkeypatch)

    job = _job(db, p, "EBOOK", payload={"preview_chain": True})
    preview_chain.finalize_preview_ebook(db, p, job)
    db.refresh(p)
    assert sent == []
    # Ainda marcamos como notificado para não tentar de novo.
    assert p.preview_notified_at is not None


def test_non_preview_ebook_does_not_email(db, monkeypatch):
    """Livro gerado fora da prévia automática não dispara o aviso de prévia pronta."""
    _, p = _seed(db)
    sent = _capture_preview_email(monkeypatch)

    job = _job(db, p, "EBOOK")
    preview_chain.finalize_preview_ebook(db, p, job)
    db.refresh(p)
    assert sent == []
    assert p.preview_notified_at is None


def test_preview_ready_email_failure_is_swallowed(db, monkeypatch):
    """Resend fora do ar não pode derrubar o job da prévia."""
    _, p = _seed(db)

    def boom(**_kwargs):
        raise RuntimeError("resend fora do ar")

    monkeypatch.setattr("app.services.transactional_email.send_preview_ready_email", boom)
    job = _job(db, p, "EBOOK", payload={"preview_chain": True})
    preview_chain.finalize_preview_ebook(db, p, job)  # não levanta
    db.refresh(p)
    assert p.book_approved_at is not None


@pytest.mark.asyncio
async def test_preview_chain_runs_with_zero_credits(db, mem_storage, monkeypatch):
    monkeypatch.setattr(handlers, "get_image_provider", lambda *a, **k: FakeImage())
    u, p = _seed(db, credits=0)
    db.add(Asset(project_id=p.id, kind=AssetKind.PHOTO.value, storage_key="photo1"))
    db.commit()

    j = _job(db, p, "AVATAR", cost=0, payload={"preview_chain": True})
    await runner.process_job(db, j)
    db.refresh(j)
    assert j.status == JobStatus.DONE.value

    story = db.scalars(
        select(Job).where(Job.project_id == p.id, Job.type == JobType.STORY.value)
    ).all()
    assert len(story) == 1
    assert story[0].status == JobStatus.PENDING.value
    db.refresh(u)
    assert u.credits == 0


@pytest.mark.asyncio
async def test_preview_chain_stops_on_insufficient_credits_when_enabled(
    db, mem_storage, monkeypatch
):
    monkeypatch.setattr(settings, "credits_enabled", True)
    monkeypatch.setattr(handlers, "get_image_provider", lambda *a, **k: FakeImage())
    u, p = _seed(db, credits=0)
    db.add(Asset(project_id=p.id, kind=AssetKind.PHOTO.value, storage_key="photo1"))
    db.commit()

    j = _job(db, p, "AVATAR", cost=0, payload={"preview_chain": True})
    await runner.process_job(db, j)
    db.refresh(j)
    assert j.status == JobStatus.DONE.value

    story = db.scalars(
        select(Job).where(Job.project_id == p.id, Job.type == JobType.STORY.value)
    ).all()
    assert len(story) == 1
    assert story[0].status == JobStatus.FAILED.value
    assert "credito" in (story[0].error or "").lower()
    db.refresh(u)
    assert u.credits == 0


@pytest.mark.asyncio
async def test_non_preview_avatar_does_not_chain(db, mem_storage, monkeypatch):
    monkeypatch.setattr(handlers, "get_image_provider", lambda *a, **k: FakeImage())
    _, p = _seed(db)
    db.add(Asset(project_id=p.id, kind=AssetKind.PHOTO.value, storage_key="photo1"))
    db.commit()
    await runner.process_job(db, _job(db, p, "AVATAR"))
    db.refresh(p)
    assert p.character_approved_at is None
    stories = db.scalars(
        select(Job).where(Job.project_id == p.id, Job.type == JobType.STORY.value)
    ).all()
    assert stories == []


def _preview_project(db, mem_storage):
    _, p = _seed(db, credits=20)
    p.character_ref = {"storage_key": "char1", "mime": "image/png"}
    p.story_text = "Título: Teste\n\nPágina 1: Uma aventura.\n\nPágina 2: Continua."
    db.commit()
    mem_storage["char1"] = b"CHAR"
    return p


@pytest.mark.asyncio
async def test_preview_ebook_fecha_com_capa_se_as_outras_imagens_travam(
    db, mem_storage, monkeypatch
):
    """A última figura não pode segurar o livro. Capa gravada + timeout segue até Prévia pronta."""
    monkeypatch.setattr("app.workers.handlers.ebook.settings.offline_fallback", False)
    monkeypatch.setattr("app.workers.handlers.ebook.settings.preview_image_timeout_s", 0.05)

    class SlowAfterCover:
        async def generate_scene(self, *, prompt="", **_kwargs):
            # A capa responde na hora; página e "na mão" ficam presas.
            if "capa de livro infantil" in prompt.lower():
                return ImageResult(image_bytes=b"COVER", mime_type="image/png", cost_usd=0.01)
            await asyncio.sleep(30)
            return ImageResult(image_bytes=b"LATE", mime_type="image/png", cost_usd=0.01)

    monkeypatch.setattr(handlers, "get_image_provider", lambda *a, **k: SlowAfterCover())
    p = _preview_project(db, mem_storage)
    j = _job(db, p, "EBOOK", payload={"preview_chain": True})
    await runner.process_job(db, j)
    db.refresh(j)
    db.refresh(p)
    assert j.status == JobStatus.DONE.value
    assert p.status == ProjectStatus.EBOOK_READY.value
    assert p.book_approved_at is not None
    covers = db.scalars(
        select(Asset).where(Asset.project_id == p.id, Asset.kind == AssetKind.COVER.value)
    ).all()
    pages = db.scalars(
        select(Asset).where(Asset.project_id == p.id, Asset.kind == AssetKind.PAGE_IMAGE.value)
    ).all()
    hands = db.scalars(
        select(Asset).where(Asset.project_id == p.id, Asset.kind == AssetKind.IN_HAND.value)
    ).all()
    assert len(covers) == 1
    assert pages == []
    assert hands == []


@pytest.mark.asyncio
async def test_preview_ebook_falha_uma_vez_se_nenhuma_imagem_sai(db, mem_storage, monkeypatch):
    monkeypatch.setattr("app.workers.handlers.ebook.settings.offline_fallback", False)
    monkeypatch.setattr("app.workers.handlers.ebook.settings.preview_image_timeout_s", 0.05)

    class AlwaysSlow:
        async def generate_scene(self, **_kwargs):
            await asyncio.sleep(30)
            raise ProviderError("nao devia chegar", transient=True)

    monkeypatch.setattr(handlers, "get_image_provider", lambda *a, **k: AlwaysSlow())
    p = _preview_project(db, mem_storage)
    j = _job(db, p, "EBOOK", payload={"preview_chain": True})
    await runner.process_job(db, j)
    db.refresh(j)
    assert j.status == JobStatus.FAILED.value
    assert j.attempts == 1
    assert "imagens" in (j.error or "").lower()


@pytest.mark.asyncio
async def test_preview_ebook_gera_capa_e_pagina_em_paralelo(db, mem_storage, monkeypatch):
    """A página não espera a capa: as duas ficam em voo juntas (senão o passo demora 3x)."""
    monkeypatch.setattr("app.workers.handlers.ebook.settings.offline_fallback", False)

    in_flight = 0
    peak = 0
    both_started = asyncio.Event()

    class ParallelProbe:
        async def generate_scene(self, **_kwargs):
            nonlocal in_flight, peak
            in_flight += 1
            peak = max(peak, in_flight)
            if in_flight >= 2:
                both_started.set()
            await asyncio.wait_for(both_started.wait(), timeout=2)
            in_flight -= 1
            return ImageResult(image_bytes=b"IMG", mime_type="image/png", cost_usd=0.01)

    monkeypatch.setattr(handlers, "get_image_provider", lambda *a, **k: ParallelProbe())
    p = _preview_project(db, mem_storage)
    j = _job(db, p, "EBOOK", payload={"preview_chain": True})
    await runner.process_job(db, j)
    db.refresh(j)
    assert j.status == JobStatus.DONE.value
    assert peak >= 2


def test_has_active_preview_ignores_unreadable_rows():
    class Boom:
        def scalars(self, *_a, **_k):
            raise RuntimeError("json ilegivel")

        def rollback(self):
            self.rolled = True

    session = Boom()
    assert preview_chain.has_active_preview(session, uuid.uuid4()) is False
    assert session.rolled is True


def test_has_active_preview(db):
    _, p = _seed(db)
    assert preview_chain.has_active_preview(db, p.id) is False
    _job(db, p, "AVATAR", payload={"preview_chain": True})
    assert preview_chain.has_active_preview(db, p.id) is True
    # Job sem flag não conta
    j2 = _job(db, p, "STORY")
    j2.status = JobStatus.PENDING.value
    db.commit()
    # ainda True por causa do AVATAR
    assert preview_chain.has_active_preview(db, p.id) is True


def _project_with_photo(auth_client) -> str:
    pid = auth_client.post("/v1/projects", json={"style": "cartoon"}).json()["id"]
    assert (
        auth_client.post(
            f"/v1/projects/{pid}/photos", json={"content_type": "image/jpeg", "ext": "jpg"}
        ).status_code
        == 201
    )
    return pid


def test_preview_not_500_when_spend_scan_crashes(auth_client, monkeypatch):
    """Teto ligado e scan estourando não pode virar 500 na prévia."""
    from app.config import settings

    monkeypatch.setattr(settings, "daily_spend_usd_ceiling", 10.0)
    monkeypatch.setattr(settings, "daily_credits_ceiling", 0)

    def boom(*_a, **_k):
        raise RuntimeError("result json corrompido")

    monkeypatch.setattr("app.services.spend_guard.day_spend", boom)
    pid = _project_with_photo(auth_client)
    r = auth_client.post(
        f"/v1/projects/{pid}/preview",
        json={"brief": "aventura"},
        headers={"Idempotency-Key": "scan-crash"},
    )
    assert r.status_code == 202, r.text
    assert r.json()["type"] == "AVATAR"


def test_preview_not_500_when_invalidate_print_fails(auth_client, monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("print_orders indisponivel")

    monkeypatch.setattr("app.routers.projects.steps.invalidate_print", boom)
    pid = _project_with_photo(auth_client)
    r = auth_client.post(
        f"/v1/projects/{pid}/preview",
        json={"brief": "aventura"},
        headers={"Idempotency-Key": "print-crash"},
    )
    assert r.status_code == 202, r.text


def test_preview_strips_nul_from_brief(auth_client):
    pid = _project_with_photo(auth_client)
    r = auth_client.post(
        f"/v1/projects/{pid}/preview",
        json={"brief": "oi\x00mundo"},
        headers={"Idempotency-Key": "nul-brief"},
    )
    assert r.status_code == 202, r.text
    jobs = auth_client.get(f"/v1/projects/{pid}/jobs").json()
    brief = jobs[0]["result"]["payload"]["brief"]
    assert "\x00" not in brief
    assert brief == "oimundo"
