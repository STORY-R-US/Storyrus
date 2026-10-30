"""The Studio contract must gate paid work and preserve approved images."""

import io
import json
import uuid

import pytest
from PIL import Image, ImageChops
from pypdf import PdfReader
from sqlalchemy import select

from app.ai_clients.base import ImageResult, ProviderError, TextResult
from app.config import settings
from app.database import get_db
from app.main import app
from app.models import Asset, Job, Project
from app.services import book_profile
from app.workers import book_render, handlers, runner


def test_preview_watermark_crosses_the_picture():
    raw = _png()
    marked = book_render.preview_watermark(raw)
    original = Image.open(io.BytesIO(raw))
    image = Image.open(io.BytesIO(marked))
    assert image.size == original.size
    changed = sum(1 for a, b in zip(original.getdata(), image.getdata(), strict=False) if a != b)
    assert changed > original.size[0] * original.size[1] // 12


def _png():
    out = io.BytesIO()
    Image.new("RGB", (1024, 1024), (83, 119, 150)).save(out, "PNG")
    return out.getvalue()


@pytest.fixture
def studio(auth_client, monkeypatch):
    store = {}
    monkeypatch.setattr("app.storage.put_bytes", lambda k, data, mime="": store.update({k: data}))
    monkeypatch.setattr("app.storage.get_bytes", lambda k: store[k])
    monkeypatch.setattr("app.storage.presign_get", lambda k: f"https://test/{k}")
    body = {
        "style": "cartoon",
        "child_name": "Lia",
        "child_age": 4,
        "theme": "space",
        "gender": "f",
        "title": "Lia e as estrelas",
        "book_size": "M",
        "cover_type": "soft",
        "language": "pt-BR",
        "languages": ["pt-BR"],
    }
    created = auth_client.post("/v1/projects", json=body)
    assert created.status_code == 201, created.text
    pid = created.json()["id"]
    photo = auth_client.post(
        f"/v1/projects/{pid}/photos",
        json={
            "content_type": "image/png",
            "ext": "png",
            "guardian_consent": True,
            "consent_version": "2026-10-29",
        },
    )
    assert photo.status_code == 201, photo.text
    store[photo.json()["storage_key"]] = _png()
    generator = app.dependency_overrides[get_db]()
    db = next(generator)
    yield auth_client, db, pid, store
    generator.close()


async def _run(studio, path, body=None, key=None):
    client, db, pid, _ = studio
    headers = {"Idempotency-Key": key} if key else {}
    response = client.post(f"/v1/projects/{pid}/{path}", json=body or {}, headers=headers)
    assert response.status_code == 202, response.text
    job = db.get(Job, uuid.UUID(response.json()["job_id"]))
    await runner.process_job(db, job)
    db.refresh(job)
    assert job.status == "DONE", job.error
    db.expire_all()
    return job


@pytest.mark.asyncio
async def test_complete_flow_requires_each_approval_and_keeps_16_paired_pages(studio):
    client, db, pid, store = studio
    for route in (
        "story",
        "avatar",
        "ebook",
        "pages/next",
        "preview/approve",
        "story/approve",
        "avatar/approve",
    ):
        assert client.post(f"/v1/projects/{pid}/{route}", json={}).status_code == 409
    job = await _run(studio, "preview")
    p = db.get(Project, uuid.UUID(pid))
    assert p.story_text is None and p.character_ref is None
    assert p.character_approved_at is None and p.book_approved_at is None
    assert p.print_requested_at is None
    assets = client.get(f"/v1/projects/{pid}/assets").json()
    assert len(assets["previews"]) == 3
    assert assets["photo_count"] == 1
    assert job.result["progress"]["stage"] == "03_LEITURA"
    assert job.result["progress"]["done"] == 3
    assert job.result["payload"]["preview_chain"] is True
    story_job = db.scalar(select(Job).where(Job.project_id == p.id, Job.type == "STORY"))
    assert story_job is not None and story_job.status == "PENDING"
    assert client.post(f"/v1/projects/{pid}/preview/approve").status_code == 409
    await runner.process_job(db, story_job)
    db.expire_all()
    p = db.get(Project, uuid.UUID(pid))
    assert p.book_profile["stage"] == "story_ready"
    assert p.story_text
    assert client.post(f"/v1/projects/{pid}/preview/approve").status_code == 409
    assert client.post(f"/v1/projects/{pid}/story/approve").status_code == 200
    spread = next(a for a in assets["previews"] if a["role"] == "02_LIVRO_ABERTO")
    spread_image = Image.open(io.BytesIO(store[spread["url"].removeprefix("https://test/")]))
    assert spread_image.width == spread_image.height * 2
    cover = next(
        a
        for a in db.scalars(select(Asset).where(Asset.project_id == p.id))
        if (a.meta or {}).get("role") == "01_CAPA"
    )
    cover_key = cover.storage_key
    cover_bytes = store[cover_key]
    assert client.post(f"/v1/projects/{pid}/preview/approve").status_code == 200
    from app.printkit.service import get_print_order

    db.expire_all()
    get_print_order(db, uuid.UUID(pid)).payment_status = "paid"
    db.commit()
    await _run(studio, "avatar")
    assert client.post(f"/v1/projects/{pid}/pages/next").status_code == 409
    assert client.post(f"/v1/projects/{pid}/avatar/approve").status_code == 200
    assert client.post(f"/v1/projects/{pid}/pages/next", json={"page": 2}).status_code == 409
    for number in range(1, 17):
        await _run(studio, "pages/next", key=f"page-{number}")
    assets = client.get(f"/v1/projects/{pid}/assets").json()
    assert len(assets["page_versions"]) == 32
    assert (
        next(a for a in assets["previews"] if a["role"] == "01_CAPA")["url"]
        == f"https://test/{cover_key}"
    )
    assert store[cover_key] == cover_bytes
    p = db.get(Project, uuid.UUID(pid))
    assert p.book_profile["stage"] == "book_ready"
    assert p.book_approved_at is None
    pdf = PdfReader(io.BytesIO(store[p.ebook_url]))
    assert len(pdf.pages) == 18  # cover + 16 interior + back
    assert round(float(pdf.pages[1].mediabox.width) * 2.54 / 72) == 21
    assert client.post(f"/v1/projects/{pid}/book/approve").status_code == 200
    assert client.post(f"/v1/projects/{pid}/pages/next").status_code == 409


@pytest.mark.asyncio
async def test_regenerate_only_named_preview_and_retry_reuses_other_shots(studio):
    client, _, pid, _ = studio
    await _run(studio, "preview")
    before = client.get(f"/v1/projects/{pid}/assets").json()["previews"]
    await _run(studio, "preview", {"image": "02_LIVRO_ABERTO", "language": "pt-BR"})
    after = client.get(f"/v1/projects/{pid}/assets").json()["previews"]
    for shot in before:
        new = next(s for s in after if s["role"] == shot["role"])
        assert (new["url"] == shot["url"]) == (shot["role"] != "02_LIVRO_ABERTO")


def test_cover_title_and_back_brand_sit_in_the_sky():
    art = _png()
    front = book_render.front_cover(art, "Meu pai, meu heroi")
    back = book_render.back_cover(art)
    original = Image.open(io.BytesIO(art))
    titled = Image.open(io.BytesIO(front))
    branded = Image.open(io.BytesIO(back))
    bottom = (0, 700, 1024, 1024)
    assert ImageChops.difference(original.crop(bottom), titled.crop(bottom)).getbbox() is None
    assert ImageChops.difference(original.crop(bottom), branded.crop(bottom)).getbbox() is None
    assert (23, 42, 58) in list(titled.getdata())
    assert (23, 42, 58) in list(branded.getdata())
    covers = PdfReader(io.BytesIO(book_render.covers_pdf(back, front, size_cm=20)))
    assert len(covers.pages) == 2
    assert round(float(covers.pages[0].mediabox.width) * 2.54 / 72) == 21
    assert len(covers.pages[0].images) == 1


def test_print_interior_mirrors_odd_pages_and_closes_with_dedication():
    art = Image.new("RGB", (80, 80), (20, 40, 80))
    for x in range(60, 80):
        for y in range(0, 20):
            art.putpixel((x, y), (255, 0, 0))
    raw = io.BytesIO()
    art.save(raw, "PNG")
    blob = book_render.interior_pdf(
        [raw.getvalue(), raw.getvalue()], dedication="Para Lia.", size_cm=20, title="Lia"
    )
    pdf = PdfReader(io.BytesIO(blob))
    assert len(pdf.pages) == 3
    assert round(float(pdf.pages[0].mediabox.width) * 25.4 / 72, 1) == 210.0
    import fitz

    doc = fitz.open(stream=blob, filetype="pdf")

    def red_on_left(page) -> int:
        pix = page.get_pixmap(matrix=fitz.Matrix(0.25, 0.25), alpha=False)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        box = image.crop((0, 0, image.width // 4, image.height // 4))
        return sum(pixel[0] for pixel in box.getdata())

    assert red_on_left(doc[0]) > red_on_left(doc[1])
    assert doc[2].get_images()
    doc.close()


def test_text_overlay_sits_in_the_sky_and_keeps_the_photo():
    art = _png()
    version = book_render.with_text(art, "Lia encontrou uma estrela.\nEra hora de brincar.", page=1)
    first = Image.open(io.BytesIO(art))
    second = Image.open(io.BytesIO(version))
    assert (
        ImageChops.difference(
            first.crop((0, 520, 1024, 1024)), second.crop((0, 520, 1024, 1024))
        ).getbbox()
        is None
    )
    assert (23, 42, 58) in list(second.getdata())
    assert (255, 250, 242) not in list(second.getdata())


def test_partial_visual_ficha_is_completed_instead_of_failing():
    from app.workers.handlers.master_book import _fill_visual_ficha

    prepared = _fill_visual_ficha(
        {"visual_identity": "olhos castanhos", "costume": "  ", "locales": {"pt-BR": {}}},
        name="Lia",
        theme="estrelas",
        title="Lia e as estrelas",
        languages=["pt-BR", "en"],
        trait="curiosidade",
        interest="",
    )
    assert prepared["costume"].startswith("Roupa de aventura")
    assert prepared["palette"]
    assert prepared["trait"] == "curiosidade"
    assert prepared["interest"] == "estrelas"
    assert prepared["locales"]["pt-BR"]["title"] == "Lia e as estrelas"
    assert "Lia" in prepared["locales"]["en"]["left"]
    assert prepared["animal"] == ""


@pytest.mark.asyncio
async def test_missing_credits_uses_a_free_preview_and_moves_on(studio, monkeypatch):
    client, db, pid, _ = studio

    class Text:
        async def prepare_book_profile(self, *, ficha, photos):
            raise ProviderError("OpenAI 429: credit_balance_exhausted", transient=False)

    class Images:
        async def generate_scene(self, **kwargs):
            raise ProviderError("OpenAI 429: insufficient_quota", transient=False)

    monkeypatch.setattr(settings, "offline_fallback", False)
    monkeypatch.setattr(handlers, "get_text_provider", lambda *a: Text())
    monkeypatch.setattr(handlers, "get_image_provider", lambda *a: Images())
    job = await _run(studio, "preview")
    project = db.get(Project, uuid.UUID(pid))
    assert project.book_profile["stage"] == "preview_ready"
    assert project.book_profile["credits_fallback"] is True
    assert job.result["credits_fallback"] is True
    previews = client.get(f"/v1/projects/{pid}/assets").json()["previews"]
    assert {item["role"] for item in previews} == {"01_CAPA", "02_LIVRO_ABERTO", "03_LEITURA"}


@pytest.mark.asyncio
async def test_any_openai_error_still_finishes_the_preview(studio, monkeypatch):
    client, db, pid, _ = studio

    class Text:
        async def prepare_book_profile(self, *, ficha, photos):
            raise ProviderError("OpenAI 429: slow down", transient=True)

    class Images:
        async def generate_scene(self, **kwargs):
            raise ProviderError("OpenAI 500: unavailable", transient=True)

    monkeypatch.setattr(settings, "offline_fallback", False)
    monkeypatch.setattr(settings, "skip_openai", False)
    monkeypatch.setattr(handlers, "get_text_provider", lambda *a: Text())
    monkeypatch.setattr(handlers, "get_image_provider", lambda *a: Images())
    job = await _run(studio, "preview")
    project = db.get(Project, uuid.UUID(pid))
    assert job.status == "DONE"
    assert project.book_profile["stage"] == "preview_ready"
    assert client.get(f"/v1/projects/{pid}/assets").json()["previews"]


@pytest.mark.asyncio
async def test_rehearsal_skips_openai_and_keeps_each_approval(studio, monkeypatch):
    from app.services import purchase_flow

    client, db, pid, _ = studio

    class Boom:
        async def prepare_book_profile(self, **kwargs):
            raise AssertionError("openai")

        async def generate_story(self, **kwargs):
            raise AssertionError("openai")

        async def generate_scene(self, **kwargs):
            raise AssertionError("openai")

        async def generate_character(self, **kwargs):
            raise AssertionError("openai")

    monkeypatch.setattr(settings, "offline_fallback", False)
    monkeypatch.setattr(settings, "skip_openai", True)
    monkeypatch.setattr(handlers, "get_text_provider", lambda *a: Boom())
    monkeypatch.setattr(handlers, "get_image_provider", lambda *a: Boom())
    await _run(studio, "preview")
    project = db.get(Project, uuid.UUID(pid))
    assert project.book_profile["stage"] == "preview_ready"
    purchase_flow.require_paid(db, project)
    story = db.scalar(select(Job).where(Job.project_id == project.id, Job.type == "STORY"))
    assert story is not None
    await runner.process_job(db, story)
    db.expire_all()
    project = db.get(Project, uuid.UUID(pid))
    assert project.book_profile["stage"] == "story_ready"
    assert project.story_text
    assert client.get(f"/v1/projects/{pid}").status_code == 200


@pytest.mark.asyncio
async def test_missing_credits_approves_each_stage_and_continues(studio, monkeypatch):
    client, db, pid, _ = studio

    class Text:
        async def prepare_book_profile(self, *, ficha, photos):
            raise ProviderError("OpenAI 429: credit_balance_exhausted", transient=False)

        async def generate_story(self, **kwargs):
            raise ProviderError("OpenAI 429: credit_balance_exhausted", transient=False)

    class Images:
        async def generate_scene(self, **kwargs):
            raise ProviderError("OpenAI 429: insufficient_quota", transient=False)

        async def generate_character(self, **kwargs):
            raise ProviderError("OpenAI 429: insufficient_quota", transient=False)

    monkeypatch.setattr(settings, "offline_fallback", False)
    monkeypatch.setattr(handlers, "get_text_provider", lambda *a: Text())
    monkeypatch.setattr(handlers, "get_image_provider", lambda *a: Images())
    await _run(studio, "preview")
    story = db.scalar(select(Job).where(Job.project_id == uuid.UUID(pid), Job.type == "STORY"))
    assert story is not None
    await runner.process_job(db, story)
    db.expire_all()
    project = db.get(Project, uuid.UUID(pid))
    assert project.book_profile["stage"] == "story_approved"
    avatar = db.scalar(select(Job).where(Job.project_id == project.id, Job.type == "AVATAR"))
    assert avatar is not None and avatar.status == "PENDING"
    await runner.process_job(db, avatar)
    db.expire_all()
    project = db.get(Project, uuid.UUID(pid))
    assert project.book_profile["stage"] == "avatar_approved"
    assert project.character_approved_at is not None
    page = db.scalar(select(Job).where(Job.idempotency_key == f"free-page-{pid}-1"))
    assert page is not None and page.status == "PENDING"
    assert client.get(f"/v1/projects/{pid}").status_code == 200


def test_filename_style_and_size_contract():
    assert (
        book_profile.filename("pt-BR", "01_CAPA", "Lía e as estrelas!")
        == "PORTUGUES_01_CAPA_Lia_e_as_estrelas.png"
    )
    assert "olhos naturais" in book_profile.art_direction("cartoon")
    assert "fotografia editorial" in book_profile.art_direction("realistic")


@pytest.mark.asyncio
async def test_original_photos_and_approved_cover_are_sent_in_all_three_languages(
    studio, monkeypatch
):
    client, db, pid, store = studio
    p = db.get(Project, uuid.UUID(pid))
    book_profile.update(p, languages=["pt-BR", "en", "es"])
    db.commit()
    calls = []

    class Text:
        async def prepare_book_profile(self, *, ficha, photos):
            assert photos == [_png()]
            return TextResult(
                json.dumps(
                    {
                        "visual_identity": "Original face and natural eyes",
                        "costume": "Blue astronaut suit",
                        "palette": "navy and cream",
                        "animal": "",
                        "trait": "curiosity",
                        "interest": "stars",
                        "locales": {
                            language: {
                                "title": f"Localized {language}",
                                "left": "First line\nSecond line",
                                "right": "Third line\nFourth line",
                            }
                            for language in ficha["languages"]
                        },
                    }
                )
            )

    class Images:
        async def generate_scene(self, **kwargs):
            calls.append(kwargs)
            return ImageResult(_png(), cost_usd=0.01)

    monkeypatch.setattr(settings, "offline_fallback", False)
    monkeypatch.setattr(handlers, "get_text_provider", lambda *a: Text())
    monkeypatch.setattr(handlers, "get_image_provider", lambda *a: Images())
    await _run(studio, "preview")
    assert len(calls) == 9
    assert all(call["photo"] == _png() for call in calls)
    assert [call["landscape"] for call in calls] == [False, True, False] * 3
    assert all("SO os textos mudam" in call["prompt"] for call in calls[3:])
    assets = client.get(f"/v1/projects/{pid}/assets").json()["previews"]
    assert len(assets) == 9
    assert any(a["filename"].startswith("INGLES_01_CAPA_") for a in assets)
    assert (
        db.get(Project, uuid.UUID(pid)).book_profile["locales"]["pt-BR"]["title"]
        == "Lia e as estrelas"
    )
    originals = db.scalars(select(Asset).where(Asset.project_id == uuid.UUID(pid))).all()
    for preview in assets:
        original = next(
            a for a in originals if (a.meta or {}).get("filename") == preview["filename"]
        )
        assert original.storage_key.endswith(preview["filename"])
        assert preview["url"] != f"https://test/{original.storage_key}"


@pytest.mark.asyncio
async def test_partial_preview_is_never_approved_and_retry_keeps_completed_cover(
    studio, monkeypatch
):
    client, db, pid, _ = studio
    # Prepare the visual profile offline, then exercise a real provider-shaped failure.
    p = db.get(Project, uuid.UUID(pid))
    book_profile.update(
        p,
        costume="blue",
        palette="navy",
        visual_identity="photo",
        locales={
            "pt-BR": {"title": "Lia e as estrelas", "left": "Um\nDois", "right": "Tres\nQuatro"}
        },
    )
    db.commit()

    class Images:
        fail = True

        async def generate_scene(self, **kwargs):
            if kwargs["landscape"] and self.fail:
                raise ProviderError("temporary test failure", transient=False)
            return ImageResult(_png(), cost_usd=0)

    images = Images()
    monkeypatch.setattr(settings, "offline_fallback", False)
    monkeypatch.setattr(handlers, "get_image_provider", lambda *a: images)
    response = client.post(f"/v1/projects/{pid}/preview")
    job = db.get(Job, uuid.UUID(response.json()["job_id"]))
    await runner.process_job(db, job)
    assert job.status == "FAILED"
    assert client.post(f"/v1/projects/{pid}/preview/approve").status_code == 409
    before = client.get(f"/v1/projects/{pid}/assets").json()["previews"]
    assert len(before) == 1
    images.fail = False
    await _run(studio, "preview")
    after = client.get(f"/v1/projects/{pid}/assets").json()["previews"]
    assert next(a for a in after if a["role"] == "01_CAPA")["url"] == before[0]["url"]


@pytest.mark.asyncio
async def test_title_change_repaints_the_cover_and_keeps_the_story(studio):
    client, db, pid, store = studio
    project = db.get(Project, uuid.UUID(pid))
    story = "Título: Lia e as estrelas\n\nPágina 1:\nLia olhou o céu."
    book_profile.update(
        project,
        stage="story_ready",
        locales={"pt-BR": {"title": "Lia e as estrelas", "left": "Um", "right": "Dois"}},
        stories={"pt-BR": story},
        costume="roupa azul",
        palette="azul",
        trait="curiosidade",
        interest="estrelas",
        visual_identity="Lia",
    )
    project.story_text = story
    db.commit()
    response = client.put(f"/v1/projects/{pid}/preview/title", json={"title": "Lia e o mar"})
    assert response.status_code == 202, response.text
    job = db.get(Job, uuid.UUID(response.json()["job_id"]))
    await runner.process_job(db, job)
    db.expire_all()
    project = db.get(Project, uuid.UUID(pid))
    assert job.status == "DONE", job.error
    assert project.book_profile["stage"] == "story_ready"
    assert project.book_profile["title"] == "Lia e o mar"
    assert project.book_profile["locales"]["pt-BR"]["title"] == "Lia e o mar"
    assert project.story_text.startswith("Título: Lia e o mar")
    assert "Lia olhou o céu." in project.story_text
    cover = next(
        item
        for item in client.get(f"/v1/projects/{pid}/assets").json()["previews"]
        if item["role"] == "01_CAPA"
    )
    original_key = next(
        row.storage_key
        for row in db.scalars(select(Asset).where(Asset.project_id == uuid.UUID(pid)))
        if (row.meta or {}).get("role") == "01_CAPA"
    )
    original = Image.open(io.BytesIO(store[original_key]))
    served = Image.open(io.BytesIO(store[cover["url"].removeprefix("https://test/")]))
    assert (23, 42, 58) in list(original.getdata())
    assert list(served.getdata()) != list(original.getdata())
    assert "watermark_key" not in cover
    project.purchase_flow = {**(project.purchase_flow or {}), "stage": "book_ready"}
    db.commit()
    db.expire_all()
    paid = next(
        item
        for item in client.get(f"/v1/projects/{pid}/assets").json()["previews"]
        if item["role"] == "01_CAPA"
    )
    served_paid = Image.open(io.BytesIO(store[paid["url"].removeprefix("https://test/")]))
    assert list(served_paid.getdata()) == list(original.getdata())


def test_title_suggestions_are_read_only_authorized_and_rate_limited(studio, monkeypatch):
    from app.ai_clients.text_openai import OpenAITextProvider

    client, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    book_profile.update(project, stage="story_ready", stories={"pt-BR": "Lia visita a Lua."})
    db.commit()
    original = dict(project.book_profile)
    calls = []

    async def suggest(self, **kwargs):
        calls.append(kwargs)
        return [f"Lia e a aventura {i}" for i in range(5)]

    monkeypatch.setattr(OpenAITextProvider, "suggest_titles", suggest)
    endpoint = f"/v1/projects/{pid}/preview/title-suggestions"
    response = client.post(endpoint, json={"guidance": "Mais divertido"})
    assert response.status_code == 200, response.text
    assert len(response.json()["titles"]) == 5
    assert calls[0]["context"]["story"] == "Lia visita a Lua."
    assert calls[0]["guidance"] == "Mais divertido"
    db.refresh(project)
    assert project.book_profile == original
    assert not db.scalars(select(Job).where(Job.project_id == project.id)).all()
    assert client.post(endpoint.replace(pid, str(uuid.uuid4())), json={}).status_code == 404
    for _ in range(4):
        assert client.post(endpoint, json={}).status_code == 200
    assert client.post(endpoint, json={}).status_code == 429
    assert len(calls) == 5


def test_title_suggestions_respect_processing_revocation_and_provider_failure(studio, monkeypatch):
    from datetime import UTC, datetime

    from app.ai_clients.text_openai import OpenAITextProvider

    client, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    book_profile.update(project, stage="story_ready")
    db.commit()

    async def unavailable(self, **kwargs):
        raise ProviderError("secret upstream error")

    monkeypatch.setattr(OpenAITextProvider, "suggest_titles", unavailable)
    endpoint = f"/v1/projects/{pid}/preview/title-suggestions"
    response = client.post(endpoint, json={})
    assert response.status_code == 502
    assert "secret" not in response.text
    project.processing_revoked_at = datetime.now(UTC)
    db.commit()
    assert client.post(endpoint, json={}).status_code == 403


def test_pending_checkout_can_refine_title_without_changing_payment_or_delivery(studio, monkeypatch):
    from app.ai_clients.text_openai import OpenAITextProvider
    from app.printkit.service import open_print_order

    client, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    book_profile.update(project, stage="preview_approved")
    order = open_print_order(db, project, prepare=False)
    order.payment_status = "pending"
    db.commit()
    before = {column.name: getattr(order, column.name) for column in order.__table__.columns}

    async def suggest(self, **kwargs):
        return [f"Lia e a aventura {i}" for i in range(5)]

    monkeypatch.setattr(OpenAITextProvider, "suggest_titles", suggest)
    assert client.post(f"/v1/projects/{pid}/preview/title-suggestions", json={}).status_code == 200
    response = client.put(f"/v1/projects/{pid}/preview/title", json={"title": "Lia na Lua"})
    assert response.status_code == 202, response.text
    db.refresh(order)
    assert {column.name: getattr(order, column.name) for column in order.__table__.columns} == before
    assert project.book_profile["title"] == "Lia na Lua"
    assert project.book_profile["stage"] == "preview_approved"
    order.payment_status = "paid"
    db.commit()
    assert client.put(f"/v1/projects/{pid}/preview/title", json={"title": "Outro"}).status_code == 409


@pytest.mark.parametrize("stage", ["preview_ready", "story_ready", "story_approved"])
def test_preview_adjustments_accept_all_preapproval_review_stages(studio, stage):
    client, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    book_profile.update(project, stage=stage, stories={"pt-BR": "História anterior"})
    db.commit()
    response = client.put(f"/v1/projects/{pid}/preview/changes", json={
        "title": "Lia e as estrelas", "theme_description": "Aventura espacial",
        "photo_notes": "Mais estrelas na capa", "story_text": "",
    })
    assert response.status_code == 202, response.text
    db.refresh(project)
    assert project.book_profile["stage"] == "ficha"
    assert project.book_profile["stories"] is None
    assert project.purchase_flow["preview_approved_at"] is None
    job = db.get(Job, uuid.UUID(response.json()["job_id"]))
    assert job.result["payload"]["master_preview"] is True
    assert job.result["payload"]["adjustment"] == "Mais estrelas na capa"


def test_preview_adjustments_keep_pending_payment_locked(studio):
    from app.printkit.service import open_print_order

    client, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    book_profile.update(project, stage="story_approved")
    order = open_print_order(db, project, prepare=False)
    order.payment_status = "pending"
    db.commit()
    response = client.put(f"/v1/projects/{pid}/preview/changes", json={
        "title": "Lia", "theme_description": "Aventura", "photo_notes": "Mais luz",
    })
    assert response.status_code == 409
    db.refresh(project)
    assert project.book_profile["stage"] == "story_approved"
