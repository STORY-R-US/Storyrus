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
from app.models import Job, Project
from app.services import book_profile
from app.workers import book_render, handlers, runner


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
        f"/v1/projects/{pid}/photos", json={"content_type": "image/png", "ext": "png"}
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
    cover = next(a for a in assets["previews"] if a["role"] == "01_CAPA")["url"]
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
    assert next(a for a in assets["previews"] if a["role"] == "01_CAPA")["url"] == cover
    p = db.get(Project, uuid.UUID(pid))
    assert p.book_profile["stage"] == "book_ready"
    assert p.book_approved_at is None
    pdf = PdfReader(io.BytesIO(store[p.ebook_url]))
    assert len(pdf.pages) == 18  # cover + 16 interior + back
    assert round(float(pdf.pages[1].mediabox.width) * 2.54 / 72) == 20
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


def test_text_overlay_preserves_pixels_outside_text_band_and_embeds_navy():
    art = _png()
    version = book_render.with_text(art, "Lia encontrou uma estrela.\nEra hora de brincar.")
    first = Image.open(io.BytesIO(art))
    second = Image.open(io.BytesIO(version))
    assert (
        ImageChops.difference(
            first.crop((0, 0, 1024, 700)), second.crop((0, 0, 1024, 700))
        ).getbbox()
        is None
    )
    assert (23, 42, 58) in second.getdata()


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
    assert all(a["url"].endswith(a["filename"]) for a in assets)


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
