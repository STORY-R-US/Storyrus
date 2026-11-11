"""The Studio contract must gate paid work and preserve approved images."""

import io
import json
import uuid

import pytest
from PIL import Image, ImageChops
from pypdf import PdfReader
from sqlalchemy import func, select

from app.ai_clients.base import ImageResult, ProviderError, TextResult
from app.config import settings
from app.database import get_db
from app.main import app
from app.models import Asset, AssetKind, Job, Project
from app.services import book_profile
from app.workers import book_render, handlers, runner


def test_reference_layout_keeps_literal_copy_with_real_heavy_fonts_and_separate_title_block():
    from app.services import editorial_profile
    from app.workers import editorial_render as render

    profile = {"editorial": editorial_profile.snapshot("2026-11-05.2")}
    title = "ANdré no Computador"
    verses = "Lia desenha uma flor\ne, com o mouse, escolhe a cor.\nNa tela, seu jardim floresce,\ne um sorriso logo aparece."
    _, heading = render.text(_png(), title, profile, title=True)
    _, body = render.text(_png(), verses, profile)
    assert heading["text"] == title and body["text"] == verses
    assert heading["weight"] == 900 and body["weight"] == 700
    assert heading["font_sha256"] != body["font_sha256"]
    assert heading["region"][0] >= 0.4
    assert len(heading["lines"]) == 2 and len(body["lines"]) == 4
    assert body["alignment"] == "center"
    assert body["font_size"] > 40


def test_perspective_compositor_preserves_art_orientation_and_foreground():
    from app.workers import editorial_render as render

    base = Image.new("RGB", (200, 200), "white")
    base.putpixel((100, 160), (7, 19, 33))
    cover = Image.new("RGB", (100, 100), "blue")
    from PIL import ImageDraw

    ImageDraw.Draw(cover).rectangle((0, 0, 45, 45), fill="red")
    geometry = {
        "valid": True,
        "issues": [],
        "surfaces": [[[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]],
        "occlusions": [[[0.45, 0.75], [0.55, 0.75], [0.55, 0.85], [0.45, 0.85]]],
    }
    data, meta = render.mockup(render.encode(base), [render.encode(cover)], geometry)
    image = Image.open(io.BytesIO(data))
    assert image.getpixel((40, 40))[0] > 200  # red stays upper left, never mirrored
    assert image.getpixel((160, 40))[2] > 200
    assert image.getpixel((100, 160)) == (7, 19, 33)  # foreground restored exactly
    assert meta["surfaces"][0]["source_sha256"] == render.digest(render.encode(cover))
    geometry["surfaces"][0] = [[0.9, 0.1], [0.1, 0.1], [0.1, 0.9], [0.9, 0.9]]
    with pytest.raises(ValueError):
        render.mockup(render.encode(base), [render.encode(cover)], geometry)


def test_keyed_geometry_uses_visible_surface_pixels_and_preserves_hands():
    from PIL import ImageDraw

    from app.workers import editorial_render as render

    template = Image.new("RGB", (200, 200), "#fff7ec")
    draw = ImageDraw.Draw(template)
    draw.rectangle((30, 30, 170, 170), fill="#ff00ff")
    draw.rectangle((80, 27, 120, 35), fill="#ff00ff")  # subtly curved edge beyond fitted quad
    draw.rectangle((90, 150, 110, 180), fill=(7, 19, 33))
    raw = render.encode(template)
    geometry, masks = render.keyed_surfaces(raw, 1)
    output, provenance = render.mockup(raw, [_png()], geometry, visible_masks=masks)
    image = Image.open(io.BytesIO(output))
    assert image.getpixel((100, 160)) == (7, 19, 33)
    assert image.getpixel((40, 40)) != (255, 0, 255)
    assert image.getpixel((100, 28)) != (255, 0, 255)
    assert provenance["method"] == "keyed_perspective_composition"
    assert geometry["surfaces"][0][0] == pytest.approx([30 / 199, 30 / 199])
    with pytest.raises(ValueError, match="não identificada"):
        render.keyed_surfaces(_png(), 1)

    spread = Image.new("RGB", (200, 200), "#fff7ec")
    draw = ImageDraw.Draw(spread)
    draw.rectangle((10, 50, 90, 150), fill="#ff00ff")
    draw.rectangle((110, 50, 190, 150), fill="#00ffff")
    draw.line((11, 55, 11, 145), fill="#ffe6ff", width=2)
    raw = render.encode(spread)
    geometry, masks = render.keyed_surfaces(raw, 2)
    output, _ = render.mockup(raw, [_png(), _png()], geometry, visible_masks=masks)
    assert Image.open(io.BytesIO(output)).getpixel((11, 70)) != (255, 230, 255)


def test_vision_geometry_rejects_uncertain_or_malformed_book_surfaces():
    from app.workers import editorial_render as render

    geometry = {
        "valid": True,
        "issues": [],
        "surfaces": [
            [[0.05, 0.2], [0.48, 0.2], [0.48, 0.8], [0.05, 0.8]],
            [[0.52, 0.2], [0.95, 0.2], [0.95, 0.8], [0.52, 0.8]],
        ],
        "occlusions": [[[0.45, 0.6], [0.5, 0.6], [0.5, 0.7], [0.45, 0.7]]],
    }
    checked = render.validate_geometry(geometry, 2)
    assert checked["surfaces"][0][0] == pytest.approx(geometry["surfaces"][0][0])
    assert checked["occlusions"][0][0] == pytest.approx(geometry["occlusions"][0][0])

    malformed = {**geometry, "surfaces": list(reversed(geometry["surfaces"]))}
    with pytest.raises(ValueError, match="ordem incorreta"):
        render.validate_geometry(malformed, 2)
    uncertain = {**geometry, "valid": False, "issues": ["gutter unclear"]}
    with pytest.raises(ValueError, match="não foram identificadas"):
        render.validate_geometry(uncertain, 2)


def test_editorial_literal_text_accents_and_overflow_fail_without_shrinking():
    from app.services import editorial_profile
    from app.workers import editorial_render as render

    profile = {"editorial": editorial_profile.snapshot("2026-11-05.1")}
    literal = "ANdré vê o céu.\nÉ tempo de aprender!"
    _, layout = render.text(_png(), literal, profile)
    assert layout["text"] == literal
    assert layout["weight"] == 500
    assert layout["line_height"] == 1.2
    x0, y0, x1, y1 = layout["ink_region_with_margin"]
    assert 0 < x0 < x1 < 1 and 0 < y0 < y1 < 1
    assert y1 < layout["region"][3]  # reserve actual lettering, not the whole wrap box
    with pytest.raises(ValueError, match="não cabe"):
        render.text(_png(), "Texto aprovado extenso. " * 300, profile)
    wide = Image.new("RGB", (200, 100), "white")
    with pytest.raises(ValueError, match="quadrada"):
        render.text(render.encode(wide), literal, profile)


@pytest.fixture
def composed_studio(studio, monkeypatch):
    from app.services import editorial_profile

    monkeypatch.setattr(editorial_profile, "CURRENT_VERSION", "2026-11-05.1")
    client, db, pid, store = studio
    project = db.get(Project, uuid.UUID(pid))
    book_profile.update(
        project,
        editorial=editorial_profile.snapshot(),
        costume="Camisa azul",
        locales={
            "pt-BR": {
                "title": "ANdré no Computador",
                "left": "André aprende com alegria.",
                "right": "Uma descoberta a cada dia.",
            }
        },
    )
    db.commit()
    calls = []
    control = {"fail_reading": False, "reject": False}

    class Images:
        async def generate_scene(self, **kwargs):
            calls.append(kwargs)
            assert kwargs["photo"] == (None if kwargs.get("landscape") else _png())
            if control["fail_reading"] and "Protagonista original segura" in kwargs["prompt"]:
                raise ProviderError("interrupção controlada", transient=False)
            image = Image.new("RGB", (1024, 1024), (min(len(calls) * 20, 240), 120, 160))
            if "#ff00ff" in kwargs["prompt"]:
                from PIL import ImageDraw

                image.paste("#fff7ec", (0, 0, 1024, 1024))
                draw = ImageDraw.Draw(image)
                if kwargs.get("landscape"):
                    draw.rectangle((51, 256, 502, 768), fill="#ff00ff")
                    draw.rectangle((522, 256, 973, 768), fill="#00ffff")
                else:
                    if "ENQUADRAMENTO OBRIGATÓRIO" in kwargs["prompt"] and not control.get(
                        "large_book"
                    ):
                        draw.rectangle((359, 543, 687, 871), fill="#ff00ff")
                    else:
                        draw.rectangle((205, 205, 819, 819), fill="#ff00ff")
            from app.workers.editorial_render import encode

            return ImageResult(encode(image), cost_usd=0)

    class Text:
        async def moderate_book_input(self, **kwargs):
            return TextResult(
                text='{"flagged": false}',
                cost_usd=0,
                meta={"flagged": False, "model": "omni-moderation-latest"},
            )

        async def generate_editorial_story(self, **kwargs):
            return TextResult(
                text="Título: "
                + kwargs["brief"]["title"]
                + "\n\n"
                + "\n\n".join(
                    f"Página {i}:\nAndré observa o céu.\nÉ tempo de aprender!" for i in range(1, 17)
                ),
                cost_usd=0,
            )

        async def plan_editorial_page(self, **kwargs):
            observed_too_small = False
            if kwargs.get("scene_image"):
                control["observed_layout_calls"] = control.get("observed_layout_calls", 0) + 1
                observed_too_small = control.pop("observed_too_small_once", False) or control.get(
                    "observed_always_too_small", False
                )
            return TextResult(
                text=json.dumps(
                    {
                        "action": kwargs["action"],
                        "text_region": [0.07, 0.07, 0.09, 0.09]
                        if observed_too_small
                        else control.get("body_initial_region", [0.09, 0.06, 0.91, 0.29])
                        if not kwargs["title"] and not kwargs.get("scene_image")
                        else [0.09, 0.06, 0.91, 0.29],
                        "alignment": "center" if kwargs["title"] else "left",
                        "protected_content": ["rosto", "mãos"],
                    }
                ),
                cost_usd=0,
            )

        async def locate_book_surfaces(self, **kwargs):
            surfaces = (
                [[[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8]]]
                if kwargs["count"] == 1
                else [
                    [[0.05, 0.25], [0.49, 0.25], [0.49, 0.75], [0.05, 0.75]],
                    [[0.51, 0.25], [0.95, 0.25], [0.95, 0.75], [0.51, 0.75]],
                ]
            )
            return TextResult(
                text=json.dumps(
                    {"valid": True, "issues": [], "surfaces": surfaces, "occlusions": []}
                ),
                cost_usd=0,
            )

        async def validate_editorial_preview(self, **kwargs):
            reading_failure = control.get("reject_reading") and kwargs["prompt"].startswith(
                "LEITURA"
            )
            body_overlap = (
                control.get("reject_body_region_once")
                and kwargs["prompt"].startswith("ARTE_BASE")
                and '"alignment": "left"' in kwargs["prompt"]
            )
            if body_overlap:
                control["reject_body_region_once"] = False
            overlap = control.get("reject_cover_text_once") and kwargs["prompt"].startswith(
                "CAPA_PLANA"
            )
            if overlap:
                control["reject_cover_text_once"] = False
                assert '"font_sha256"' in kwargs["prompt"]
            return TextResult(
                text=json.dumps(
                    {
                        "valid": not (
                            control["reject"] or overlap or body_overlap or reading_failure
                        ),
                        "issues": ["texto sobre o cabelo"]
                        if overlap
                        else ["texto invade a mão"]
                        if body_overlap
                        else ["anatomia das mãos incorreta"]
                        if reading_failure
                        else ["identidade incorreta"]
                        if control["reject"]
                        else [],
                        "limitations": [],
                    }
                ),
                cost_usd=0,
                meta={"review_scope": "text_reserve"} if body_overlap else {},
            )

    monkeypatch.setattr(settings, "offline_fallback", False)
    monkeypatch.setattr(handlers, "get_image_provider", lambda: Images())
    monkeypatch.setattr(handlers, "get_text_provider", lambda: Text())
    yield studio, calls, control


@pytest.fixture
def reference_studio(composed_studio):
    from app.services import editorial_profile

    studio, calls, control = composed_studio
    _, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    project.style = "realistic"
    book_profile.update(
        project,
        editorial=editorial_profile.snapshot("2026-11-05.2"),
        scene_world="Ateliê ilustrado com luz suave, mesa de madeira e plantas",
        preview_actions={
            "pt-BR": {
                "left": "Lia desenha uma flor e escolhe a cor no computador",
                "right": "Lia nomeia e salva o desenho em uma pasta",
            }
        },
        locales={
            "pt-BR": {
                "title": "Lia no computador",
                "left": "Lia desenha uma flor\ne escolhe a sua cor.\nSeu jardim vai florescer,\nhá tanto para aprender.",
                "right": "Dá um nome à criação\ne salva com atenção.\nDepois sabe encontrar\nseu jardim para admirar.",
            }
        },
    )
    db.commit()
    return studio, calls, control


@pytest.mark.asyncio
async def test_reference_pipeline_uses_actions_illustrated_setting_and_new_typography(
    reference_studio,
):
    studio, calls, _ = reference_studio
    job = await _run(studio, "preview", key="reference-style")
    assert job.status == "DONE"
    assert len(calls) == 4
    assert "TOP QUARTER" not in calls[0]["prompt"]
    assert "ABAIXO de 25%" not in calls[0]["prompt"]
    assert "COVER DESIGN" in calls[0]["prompt"]
    assert "HAND-PAINTED" in calls[0]["style"]
    assert "desenha uma flor" in calls[1]["prompt"]
    assert "salva o desenho" in calls[2]["prompt"]
    assert "escala natural" in calls[-1]["prompt"]
    client, db, pid, _ = studio
    sources = db.scalars(
        select(Asset).where(Asset.project_id == uuid.UUID(pid), Asset.kind == "editorial_source")
    ).all()
    layouts = {a.meta["stage"]: a.meta["layout"] for a in sources if a.meta.get("layout")}
    assert layouts["cover:text"]["weight"] == 900
    assert layouts["preview:left:text"]["weight"] == 700
    assert layouts["preview:right:text"]["alignment"] == "center"
    assert len(client.get(f"/v1/projects/{pid}/assets").json()["previews"]) == 3
    assert client.post(f"/v1/projects/{pid}/story").status_code == 409


@pytest.mark.asyncio
async def test_mockup_falls_back_to_vision_geometry_without_regenerating_images(
    composed_studio, monkeypatch
):
    from app.workers import editorial_render as render

    studio, calls, _ = composed_studio

    def missing_key_pixels(_data, _count):
        raise ValueError("Superfície de impressão não identificada pelos pixels")

    monkeypatch.setattr(render, "keyed_surfaces", missing_key_pixels)
    await _run(studio, "preview", key="vision-geometry-fallback")
    assert len(calls) == 4  # flat art plus the optional holding scene

    _, db, pid, _ = studio
    sources = db.scalars(
        select(Asset).where(Asset.project_id == uuid.UUID(pid), Asset.kind == "editorial_source")
    ).all()
    mockups = {asset.meta["stage"]: asset for asset in sources if asset.meta.get("stage")}
    assert mockups["spread"].meta["composition"]["method"] == "deterministic_open_book_v1"
    assert mockups["reading"].meta["surface_detection"]["method"] == "vision"
    assert mockups["reading"].meta["composition"]["method"] == "vision_geometry_composition"
    assert (
        "impressão não identificada"
        in mockups["reading"].meta["surface_detection"]["keying_fallback_reason"]
    )


@pytest.mark.asyncio
async def test_reference_pipeline_leaves_book_scale_judgement_to_user(reference_studio):
    studio, _, control = reference_studio
    control["large_book"] = True
    client, db, pid, _ = studio
    response = client.post(
        f"/v1/projects/{pid}/preview", headers={"Idempotency-Key": "oversized-book"}
    )
    job = db.get(Job, uuid.UUID(response.json()["job_id"]))
    await runner.process_job(db, job)
    assert job.status == "DONE", job.error
    assert job.result["scenes"]["pt-BR:03_LEITURA"]["state"] == "awaiting_user_review"
    assert client.get(f"/v1/projects/{pid}/preview/package").status_code == 200

    assert not (db.get(Project, uuid.UUID(pid)).purchase_flow or {}).get("preview_approved_at")


def test_new_preview_version_refreshes_only_generated_drafts_and_preserves_literal_text(studio):
    from app.services import editorial_profile

    _, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    book_profile.update(
        project,
        editorial=editorial_profile.snapshot("2026-11-05.1"),
        locales={
            "pt-BR": {
                "title": "tÍTULO literal",
                "left": "Texto meu.\nNão alterar.",
                "right": "Verso automático.",
            }
        },
        text_record={
            "pt-BR": {
                "title": {"origin": "user_supplied"},
                "left": {"origin": "user_supplied"},
                "right": {"origin": "generated"},
            }
        },
    )
    previous = project.book_profile
    assert book_profile.adopt_current_editorial_draft(project)
    assert project.book_profile["editorial"]["version"] == "2026-11-05.3"
    assert project.book_profile["supplied_locales"]["pt-BR"] == {
        "title": "tÍTULO literal",
        "left": "Texto meu.\nNão alterar.",
    }
    assert project.book_profile["locales"] == {}
    project.book_profile = previous
    project.purchase_flow = {"preview_approved_at": "2026-11-05"}
    assert not book_profile.adopt_current_editorial_draft(project)
    assert project.book_profile == previous


@pytest.mark.asyncio
async def test_body_layout_adapts_to_observed_art_without_regenerating_scene(composed_studio):
    studio, calls, control = composed_studio
    control["body_initial_region"] = [0.07, 0.07, 0.09, 0.09]
    control["observed_always_too_small"] = True
    control["reject_body_region_once"] = True
    job = await _run(studio, "preview", key="observed-body-layout")
    assert job.status == "DONE"
    assert len(calls) == 4
    assert control["observed_layout_calls"] == 6
    _, db, pid, _ = studio
    sources = db.scalars(
        select(Asset).where(Asset.project_id == uuid.UUID(pid), Asset.kind == "editorial_source")
    ).all()
    pages = [a for a in sources if a.meta["stage"] in {"preview:left:text", "preview:right:text"}]
    assert len(pages) == 2
    layouts = {a.meta["stage"]: a.meta["layout"]["region"] for a in pages}
    assert layouts["preview:left:text"] != [0.07, 0.07, 0.93, 0.37]
    assert layouts["preview:right:text"] == [0.07, 0.07, 0.93, 0.37]


@pytest.mark.asyncio
async def test_composed_provider_failure_does_not_consume_visual_retries(composed_studio):
    from app.workers.handlers.editorial_book import Pipeline

    studio, _, _ = composed_studio
    client, db, pid, _ = studio
    response = client.post(f"/v1/projects/{pid}/preview")
    job = db.get(Job, uuid.UUID(response.json()["job_id"]))
    pipe = Pipeline(db, job, db.get(Project, uuid.UUID(pid)), [_png()])

    async def unavailable(attempt):
        raise ProviderError("temporary outage", transient=True, status_code=503)

    with pytest.raises(ProviderError, match="temporary outage") as captured:
        await pipe.stage("cover:art", {}, unavailable)
    assert "Etapa editorial cover:art" in str(captured.value)
    task = job.result["editorial_tasks"]["cover:art"]
    assert task["state"] == "provider_failed"
    assert task["provider_status"] == 503
    assert task["attempts"] == 0

    async def restored(attempt):
        assert attempt == 1
        return _png(), {}

    data, _ = await pipe.stage("cover:art", {}, restored)
    assert data == _png()
    assert job.result["editorial_tasks"]["cover:art"]["state"] == "passed"


@pytest.mark.asyncio
async def test_composed_full_cover_overlap_stops_without_replacing_art(composed_studio):
    studio, calls, control = composed_studio
    control["reject_cover_text_once"] = True
    job = await _run(studio, "preview", key="repair-text-overlap", expected="FAILED")
    assert job.status == "FAILED"
    assert "texto sobre o cabelo" in job.error
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_composed_three_scenes_resume_exact_sources_and_purchase_gates(composed_studio):
    from app.services import editorial_profile
    from app.workers.editorial_render import digest

    studio, calls, control = composed_studio
    client, db, pid, store = studio
    control["reject_reading"] = True
    response = client.post(f"/v1/projects/{pid}/preview")
    job = db.get(Job, uuid.UUID(response.json()["job_id"]))
    await runner.process_job(db, job)
    assert job.status == "DONE", job.error
    assert len(calls) == 4  # three flat arts and one optional holding scene
    assert len(client.get(f"/v1/projects/{pid}/assets").json()["previews"]) == 3
    assert not (db.get(Project, uuid.UUID(pid)).purchase_flow or {}).get("preview_approved_at")
    reading_asset = next(
        a
        for a in db.scalars(select(Asset).where(Asset.project_id == uuid.UUID(pid))).all()
        if a.kind == AssetKind.IN_HAND.value and a.meta.get("workflow") == 1
    )
    assert reading_asset.meta["presentation"] == "book_only_fallback"
    assert reading_asset.meta["validation"]["status"] == "awaiting_user_review"
    assert (
        client.get(f"/v1/projects/{pid}/assets").json()["in_hand_presentation"]
        == "book_only_fallback"
    )
    control["reject_reading"] = False
    before_retry = len(calls)
    await _run(studio, "preview", key="resume-composed")
    assert len(calls) == before_retry  # reuse the exact fallback without another paid attempt
    assets = [
        a
        for a in db.scalars(select(Asset).where(Asset.project_id == uuid.UUID(pid)))
        if (a.meta or {}).get("workflow") == 1
        and (a.meta or {}).get("role") in editorial_profile.ROLES
    ]
    assert len(assets) == 3
    cover = next(a for a in assets if a.meta["role"] == "01_CAPA")
    reading = next(a for a in assets if a.meta["role"] == "03_LEITURA")
    assert reading.meta["composition"]["source"] == digest(store[cover.meta["flat_cover_key"]])
    assert store[cover.meta["flat_cover_key"]] != store[cover.storage_key]
    assert client.get(f"/v1/projects/{pid}/preview/package").status_code == 200
    assert client.post(f"/v1/projects/{pid}/story").status_code == 409
    assert client.post(f"/v1/projects/{pid}/preview/approve").status_code == 200
    assert client.post(f"/v1/projects/{pid}/story").status_code == 409
    from app.printkit.service import _approved_cover

    assert (
        _approved_cover(db, db.get(Project, uuid.UUID(pid))) == store[cover.meta["flat_cover_key"]]
    )


@pytest.mark.asyncio
async def test_composed_rejects_identity_with_bounded_retries(composed_studio):
    studio, calls, control = composed_studio
    control["reject"] = True
    client, db, pid, _ = studio
    response = client.post(f"/v1/projects/{pid}/preview")
    job = db.get(Job, uuid.UUID(response.json()["job_id"]))
    await runner.process_job(db, job)
    assert job.status == "FAILED"
    assert len(calls) == 1
    assert not db.get(Project, uuid.UUID(pid)).purchase_flow.get("preview_ready_at")
    assert client.get(f"/v1/projects/{pid}/preview/package").status_code == 409


@pytest.mark.asyncio
async def test_composed_text_edit_reuses_art_and_preserves_locked_text(composed_studio):
    from app.workers.handlers.editorial_book import Pipeline

    studio, calls, _ = composed_studio
    client, db, pid, _ = studio
    accepted = client.post(f"/v1/projects/{pid}/preview")
    job = db.get(Job, uuid.UUID(accepted.json()["job_id"]))
    project = db.get(Project, uuid.UUID(pid))
    pipe = Pipeline(db, job, project, [_png()])
    _, first = await pipe.art("page:1", "A pessoa observa o céu.", value="A pessoa observa o céu.")
    _, second = await pipe.art(
        "page:1", "A pessoa observa o céu.", value="André olha o céu.\nÉ tempo de aprender!"
    )
    assert len(calls) == 1
    assert first["art_key"] == second["art_key"]
    assert second["layout"]["text"] == "André olha o céu.\nÉ tempo de aprender!"


@pytest.mark.asyncio
@pytest.mark.parametrize("language,prefix", [("en", "INGLES"), ("es", "ESPANHOL")])
async def test_composed_selected_language_delivers_only_three_pngs(
    composed_studio, language, prefix
):
    import zipfile

    studio, _, _ = composed_studio
    client, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    locale = project.book_profile["locales"]["pt-BR"]
    project.language = language
    book_profile.update(project, languages=[language], locales={language: locale})
    db.commit()
    await _run(studio, "preview")
    response = client.get(f"/v1/projects/{pid}/preview/package")
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert len(archive.namelist()) == 3
        assert all(name.startswith(prefix) for name in archive.namelist())


@pytest.mark.asyncio
async def test_composed_paid_page_uses_same_policy_and_keeps_text_layer(composed_studio):
    from app.printkit.service import get_print_order

    studio, calls, _ = composed_studio
    client, db, pid, store = studio
    await _run(studio, "preview")
    assert client.post(f"/v1/projects/{pid}/preview/approve").status_code == 200
    project = db.get(Project, uuid.UUID(pid))
    order = get_print_order(db, project.id)
    order.payment_status = "paid"
    db.commit()
    await _run(studio, "story")
    assert client.post(f"/v1/projects/{pid}/story/approve").status_code == 200
    project.character_ref = {"storage_key": "test-avatar"}
    store["test-avatar"] = _png()
    project.character_approved_at = project.created_at
    story = "Título: ANdré no Computador\n\n" + "\n\n".join(
        f"Página {i}:\nAndré observa o céu.\nÉ tempo de aprender!" for i in range(1, 17)
    )
    book_profile.update(project, stage="avatar_approved", stories={"pt-BR": story})
    db.commit()
    before = len(calls)
    await _run(studio, "pages/next", {"page": 1})
    assert len(calls) == before + 1
    pages = client.get(f"/v1/projects/{pid}/assets").json()["page_versions"]
    assert len(pages) == 2
    rendered = next(p for p in pages if p["role"] == "com_texto")
    assert rendered["layout"]["text"] == "André observa o céu.\nÉ tempo de aprender!"
    assert rendered["layout"]["weight"] == 500
    assert rendered["validation"]["status"] == "valid"
    assert "sem simulação de livro" in calls[-1]["prompt"].lower()
    assert "o mobiliário da história é permitido" in calls[-1]["prompt"].lower()


@pytest.mark.asyncio
async def test_composed_title_edit_reuses_cover_art_and_refreshes_reading(composed_studio):
    studio, calls, _ = composed_studio
    client, db, pid, _ = studio
    await _run(studio, "preview")
    before = len(calls)
    response = client.put(f"/v1/projects/{pid}/preview/title", json={"title": "Um Novo Título"})
    assert response.status_code == 202
    job = db.get(Job, uuid.UUID(response.json()["job_id"]))
    await runner.process_job(db, job)
    assert job.status == "DONE", job.error
    assert len(calls) == before + 1  # only the dependent reading scene needs generation
    assert client.get(f"/v1/projects/{pid}/preview/package").status_code == 200


def test_preview_watermark_crosses_the_picture():
    raw = _png()
    marked = book_render.preview_watermark(raw)
    original = Image.open(io.BytesIO(raw))
    image = Image.open(io.BytesIO(marked))
    assert image.size == original.size
    changed = sum(1 for a, b in zip(original.getdata(), image.getdata(), strict=False) if a != b)
    assert changed > original.size[0] * original.size[1] // 12


def test_editorial_preview_png_dimensions_are_normalized_without_stretching():
    wide = io.BytesIO()
    Image.new("RGB", (1200, 800), (20, 30, 40)).save(wide, "PNG")
    cover = Image.open(io.BytesIO(book_render.png(wide.getvalue(), square=True)))
    spread = Image.open(io.BytesIO(book_render.png(wide.getvalue(), spread=True)))
    assert cover.width == cover.height == 1200
    assert spread.width == spread.height * 2


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
    # This suite exercises the pre-existing contract, including paid-book gates.
    legacy = db.get(Project, uuid.UUID(pid))
    profile = dict(legacy.book_profile)
    profile.pop("editorial", None)
    profile["languages"] = ["pt-BR"]
    legacy.book_profile = profile
    db.commit()
    yield auth_client, db, pid, store
    generator.close()


async def _run(studio, path, body=None, key=None, expected="DONE"):
    client, db, pid, _ = studio
    headers = {"Idempotency-Key": key} if key else {}
    response = client.post(f"/v1/projects/{pid}/{path}", json=body or {}, headers=headers)
    assert response.status_code == 202, response.text
    job = db.get(Job, uuid.UUID(response.json()["job_id"]))
    await runner.process_job(db, job)
    db.refresh(job)
    assert job.status == expected, job.error
    db.expire_all()
    return job


@pytest.mark.asyncio
async def test_preview_catches_impossible_body_before_buying_cover(reference_studio):
    from app.services import book_design

    studio, calls, _ = reference_studio
    client, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    locales = project.book_profile["locales"]
    locales["pt-BR"]["left"] = "Texto extenso. " * 500
    book_profile.update(project, locales=locales, book_design=book_design.snapshot("family"))
    db.commit()
    response = client.post(f"/v1/projects/{pid}/preview", json={"cover_only": True})
    assert response.status_code == 202
    job = db.get(Job, uuid.UUID(response.json()["job_id"]))
    await runner.process_job(db, job)
    assert job.status == "FAILED"
    assert "Encurte" in job.error and "página esquerda" in job.error
    assert calls == []


@pytest.mark.asyncio
async def test_long_title_and_layout_upgrade_reuse_the_purchased_art(reference_studio, monkeypatch):
    from app.services import book_design
    from app.workers import editorial_render

    studio, calls, _ = reference_studio
    _, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    locales = project.book_profile["locales"]
    literal = "João Pedro e suas extraordinárias descobertas no parque"
    locales["pt-BR"]["title"] = literal
    book_profile.update(project, locales=locales, book_design=book_design.snapshot("family"))
    db.commit()
    await _run(studio, "preview", {"cover_only": True}, key="long-title")
    assert len(calls) == 1
    first = project.book_profile["cover_calibration"]["flat_meta"]
    assert first["layout"]["text"] == literal and first["layout"]["fit_adjusted"]
    monkeypatch.setattr(editorial_render, "TEXT_LAYOUT_REVISION", "next-local-layout")
    await _run(studio, "preview", {"cover_only": True}, key="local-layout-upgrade")
    second = project.book_profile["cover_calibration"]["flat_meta"]
    assert len(calls) == 1
    assert first["art_key"] == second["art_key"]
    assert second["layout"]["text_layout_revision"] == "next-local-layout"


def test_failed_preview_copy_can_be_saved_without_starting_generation(reference_studio):
    from app.printkit.service import get_print_order

    studio, calls, _ = reference_studio
    client, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    literal = {
        "title": "João no parque",
        "left": "João olha o céu.\nQue lindo dia!",
        "right": "Brinca no parque.\nCom alegria!",
    }
    before = db.scalar(select(func.count(Job.id)))
    response = client.put(f"/v1/projects/{pid}/preview/copy", json=literal)
    assert response.status_code == 200, response.text
    assert response.json()["book_profile"]["locales"]["pt-BR"] == literal
    db.refresh(project)
    assert db.scalar(select(func.count(Job.id))) == before
    assert not calls
    response = client.put(
        f"/v1/projects/{pid}/preview/copy", json={**literal, "left": "Texto extenso. " * 100}
    )
    assert response.status_code == 422
    assert project.book_profile["locales"]["pt-BR"] == literal
    get_print_order(db, project.id).payment_status = "paid"
    db.commit()
    assert client.put(f"/v1/projects/{pid}/preview/copy", json=literal).status_code == 409


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["family", "adventure", "cartoon"])
@pytest.mark.parametrize("role", ["01_CAPA", "02_LIVRO_ABERTO", "03_LEITURA"])
async def test_catalog_improvements_reach_provider_without_restarting_cover(
    reference_studio, model, role
):
    studio, calls, _ = reference_studio
    _, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    project.style = "cartoon" if model == "cartoon" else "realistic"
    db.commit()
    await _run(
        studio, "preview", {"catalog_design_id": model, "cover_only": True}, key="first-cover"
    )
    if role != "01_CAPA":
        await _run(
            studio,
            "preview",
            {"approved_cover_sha256": project.book_profile["cover_calibration"]["sha256"]},
            key="approve-first-cover",
        )
    before = len(calls)
    instruction = "Acrescente uma pequena pipa roxa no fundo da cena"
    job = await _run(
        studio, "preview", {"image": role, "adjustment": instruction}, key="requested-improvement"
    )
    assert len(calls) > before
    assert all(instruction in call["prompt"] for call in calls[before:])
    assert project.book_profile["stage"] == (
        "cover_ready" if role == "01_CAPA" else "preview_ready"
    )
    assert job.result["preview_complete"] == (role != "01_CAPA")


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["family", "adventure", "cartoon"])
async def test_complete_catalog_design_controls_preview_and_paid_pages(reference_studio, model):
    from app.printkit.service import get_print_order
    from app.services import book_design

    studio, calls, _ = reference_studio
    client, db, pid, store = studio
    project = db.get(Project, uuid.UUID(pid))
    if model == "cartoon":
        project.style = "cartoon"
    db.commit()
    await _run(studio, "preview", {"catalog_design_id": model, "cover_only": True})
    project = db.get(Project, uuid.UUID(pid))
    design = book_design.resolve(project.book_profile)
    assert design["id"] == model
    assert len(calls) == 1
    assert project.book_profile["stage"] == "cover_ready"
    approval = project.book_profile["cover_calibration"]["sha256"]
    await _run(studio, "preview", {"approved_cover_sha256": approval}, key="continue-catalog")
    assert len(calls) == 4
    expected_roles = ["cover", "page", "page", "holding"]
    for call, role in zip(calls, expected_roles, strict=True):
        references = [call["character_ref"], *call.get("extra_refs", [])]
        assert book_design.reference(design, role) not in references
        assert "COMPLETE CATALOG BOOK DESIGN" in call["prompt"]
        assert "AUTHORIZED CAST" in call["prompt"]
    assert calls[0]["extra_refs"] == []
    assert "SINGLE FRONT COVER ONLY" in calls[0]["prompt"]
    assert '"solo": true' in calls[0]["prompt"]
    assert not (project.purchase_flow or {}).get("preview_approved_at")
    sources = db.scalars(
        select(Asset).where(Asset.project_id == project.id, Asset.kind == "editorial_source")
    ).all()
    layouts = {a.meta["stage"]: a.meta["layout"] for a in sources if a.meta.get("layout")}
    if model == "family":
        locale = project.book_profile["locales"]["pt-BR"]
        assert layouts["preview:left:text"]["text"] == locale["left"]
        assert layouts["preview:right:text"]["text"] == locale["right"]
        for call in calls[1:3]:
            assert '"role": "preview_page"' in call["prompt"]
            assert '"mode": "two_scenes"' in call["prompt"]
            assert "quiet decorative reading page" not in call["prompt"]
        assert "two distinct rigid boards" in calls[-1]["prompt"]
        assert "contact shadows" in calls[-1]["prompt"]
    elif model != "adventure":
        locale = project.book_profile["locales"]["pt-BR"]
        assert layouts["preview:reading:text"]["text"] == locale["left"] + "\n\n" + locale["right"]
        assert layouts["preview:illustration:text"]["illustration_only"]
    assert client.post(f"/v1/projects/{pid}/preview/approve").status_code == 200
    get_print_order(db, project.id).payment_status = "paid"
    project.character_ref = {"storage_key": "test-avatar"}
    store["test-avatar"] = _png()
    project.character_approved_at = project.created_at
    passages = [f"Lia observa a flor {i:02d}." for i in range(1, 17)]
    story = "Título: Lia\n\n" + "\n\n".join(
        f"Página {i}:\n{passage}" for i, passage in enumerate(passages, 1)
    )
    book_profile.update(project, stage="avatar_approved", stories={"pt-BR": story})
    db.commit()
    before = len(calls)
    if model == "family":
        broken_story = story.replace(passages[14], "Texto extenso. " * 500)
        book_profile.update(project, stories={"pt-BR": broken_story})
        db.commit()
        response = client.post(
            f"/v1/projects/{pid}/pages/next",
            json={"page": 1},
            headers={"Idempotency-Key": "invalid-later-page"},
        )
        job = db.get(Job, uuid.UUID(response.json()["job_id"]))
        await runner.process_job(db, job)
        assert job.status == "FAILED" and "página 15" in job.error
        assert len(calls) == before
        book_profile.update(project, stories={"pt-BR": story})
        db.commit()
    for number in (1, 2):
        await _run(studio, "pages/next", {"page": number}, key=f"catalog-page-{number}")
    assert len(calls) == before + 2
    pages = client.get(f"/v1/projects/{pid}/assets").json()["page_versions"]
    rendered = [p for p in pages if p["role"] == "com_texto"]
    assert len(rendered) == 2
    combined = "\n".join(p["layout"]["text"] for p in rendered)
    assert all(combined.count(passage) == 1 for passage in passages[:2])
    for call in calls[before:]:
        assert book_design.reference(design, "page") not in call["extra_refs"]
        assert len(call["extra_refs"]) >= 1  # this project's approved cover only
    if model == "family":
        from app.workers.handlers.master_book import _assets

        revised = story.replace(passages[1], "Lia rega a flor com carinho.")
        book_profile.update(project, stories={"pt-BR": revised})
        db.commit()
        before = len(calls)
        await _run(studio, "pages/next", {"page": 2}, key="correct-paired-passage")
        assert len(calls) == before + 1  # illustration only; reading text refreshes locally
        reading = _assets(db, project, workflow=1, language="pt-BR", role="com_texto", page=1)[-1]
        assert reading.meta["layout"]["text"] == passages[0] + "\n\nLia rega a flor com carinho."
        before = len(calls)
        instruction = "Mude as folhas decorativas para azul-claro"
        await _run(
            studio,
            "pages/next",
            {"page": 1, "adjustment": instruction},
            key="change-reading-background",
        )
        assert len(calls) == before + 1
        assert instruction in calls[-1]["prompt"]


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


def test_print_interior_preserves_page_orientation_and_closes_with_dedication():
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

    assert red_on_left(doc[0]) == red_on_left(doc[1])
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


def test_child_name_keeps_a_capital_on_each_part():
    assert book_profile.capitalize_child_name("lila") == "Lila"
    assert book_profile.capitalize_child_name("ana maria") == "Ana Maria"
    assert book_profile.capitalize_child_name("  ana-luiza ") == "Ana-Luiza"
    assert book_profile.capitalize_child_name("  ") is None


def test_create_project_stores_the_child_details_in_plain_language(auth_client):
    created = auth_client.post(
        "/v1/projects",
        json={
            "style": "cartoon",
            "child_name": "lila",
            "child_age": 5,
            "child_trait": "curiosa",
            "child_interest": "estrelas",
            "costume": "vestido azul",
            "gender": "f",
            "title": "Lila e as estrelas",
            "book_size": "M",
            "cover_type": "soft",
            "language": "pt-BR",
            "languages": ["pt-BR"],
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["child_name"] == "Lila"
    assert body["child_trait"] == "curiosa"
    assert body["child_interest"] == "estrelas"
    assert body["book_profile"]["costume"] == "vestido azul"


def test_child_profile_can_be_rewritten_without_generating(studio):
    client, _db, pid, _store = studio
    response = client.put(
        f"/v1/projects/{pid}/child",
        json={
            "child_name": "lila",
            "child_age": 6,
            "costume": "capa de estrelas",
            "trait": "corajosa",
            "interest": "luas",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["child_name"] == "Lila"
    assert body["child_age"] == 6
    assert body["child_trait"] == "corajosa"
    assert body["child_interest"] == "luas"
    assert body["book_profile"]["costume"] == "capa de estrelas"
    assert body["book_profile"]["stage"] == "ficha"


@pytest.mark.asyncio
async def test_paused_preview_keeps_the_details_the_adult_wrote(studio, monkeypatch):
    _client, db, pid, _store = studio
    project = db.get(Project, uuid.UUID(pid))
    project.child_name = "lila"
    project.child_trait = "corajosa"
    project.child_interest = "estrelas"
    book_profile.update(project, costume="capa de estrelas")
    db.commit()
    monkeypatch.setattr(settings, "offline_fallback", False)
    monkeypatch.setattr(settings, "skip_openai", True)
    await _run(studio, "preview")
    db.expire_all()
    assert project.child_name == "Lila"
    assert project.book_profile["costume"] == "capa de estrelas"
    assert project.book_profile["trait"] == "corajosa"
    assert project.book_profile["interest"] == "estrelas"


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
    assert "figurino definido" in prepared["costume"]
    assert prepared["palette"]
    assert prepared["trait"] == "curiosidade"
    assert prepared["interest"] == "estrelas"
    assert prepared["locales"]["pt-BR"]["title"] == "Lia e as estrelas"
    assert "Lia" in prepared["locales"]["en"]["left"]
    assert prepared["animal"] == ""


@pytest.mark.asyncio
async def test_editorial_profile_accepts_structured_identity_without_inventing_personality(
    studio, monkeypatch
):
    from app.services import editorial_profile
    from app.workers.handlers.master_book import _prepare

    _, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    book_profile.update(project, editorial=editorial_profile.snapshot())
    job = Job(project_id=project.id, type="EBOOK", status="RUNNING", cost_usd=0)
    db.add(job)
    db.commit()

    class Text:
        async def prepare_book_profile(self, **kwargs):
            return TextResult(
                text=json.dumps(
                    {
                        "visual_identity": {"eyes": "castanhos", "hair": "curto"},
                        "costume": {"shirt": "azul"},
                        "palette": ["azul", "creme"],
                        "trait": "",
                        "interest": "",
                        "animal": {},
                        "locales": {
                            "pt-BR": {
                                "title": "Lia e as estrelas",
                                "left": "Lia olha o céu.\nUma estrela apareceu.",
                                "right": "Ela aprende a observar.\nE começa a imaginar.",
                            }
                        },
                    }
                ),
                cost_usd=0,
            )

    monkeypatch.setattr(settings, "offline_fallback", False)
    monkeypatch.setattr(settings, "skip_openai", False)
    monkeypatch.setattr(handlers, "get_text_provider", lambda: Text())
    await _prepare(db, job, project, [_png()])
    assert json.loads(project.book_profile["visual_identity"])["eyes"] == "castanhos"
    assert json.loads(project.book_profile["costume"])["shirt"] == "azul"
    assert project.book_profile["trait"] == project.book_profile["interest"] == ""
    assert project.book_profile["locales"]["pt-BR"]["title"] == "Lia e as estrelas"


@pytest.mark.parametrize("identity", [None, "", {}, {"notes": ""}, []])
def test_editorial_profile_still_rejects_missing_identity(identity):
    from app.workers.handlers.master_book import _normalize_editorial_ficha

    with pytest.raises(ProviderError, match="visual_identity"):
        _normalize_editorial_ficha(
            {"visual_identity": identity, "costume": "Camisa azul", "palette": "Azul"}
        )


@pytest.mark.asyncio
async def test_editorial_review_records_general_limitations_without_rejecting_approved_image(
    composed_studio, monkeypatch
):
    from app.workers.handlers.editorial_book import Pipeline

    studio, _, _ = composed_studio
    client, db, pid, _ = studio
    accepted = client.post(f"/v1/projects/{pid}/preview")
    job = db.get(Job, uuid.UUID(accepted.json()["job_id"]))
    project = db.get(Project, uuid.UUID(pid))

    class Text:
        async def validate_editorial_preview(self, **kwargs):
            return TextResult(
                text=json.dumps(
                    {
                        "valid": True,
                        "issues": [],
                        "limitations": ["Visual identity review is probabilistic."],
                    }
                ),
                cost_usd=0,
            )

    monkeypatch.setattr(handlers, "get_text_provider", lambda: Text())
    report = await Pipeline(db, job, project, [_png()]).review(_png(), "CAPA_PLANA: título literal")
    assert report["status"] == "valid"
    assert report["limitations"] == ["Visual identity review is probabilistic."]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message", ["OpenAI 429: credit_balance_exhausted", "OpenAI 500: unavailable"]
)
@pytest.mark.parametrize("failure_stage", ["profile", "image"])
async def test_ai_errors_fail_preview_without_substitutes_or_automatic_approvals(
    studio, monkeypatch, message, failure_stage
):
    client, db, pid, _ = studio

    class Text:
        async def moderate_book_input(self, **kwargs):
            return TextResult(
                text='{"flagged": false}',
                cost_usd=0,
                meta={"flagged": False, "model": "omni-moderation-latest"},
            )

        async def prepare_book_profile(self, **kwargs):
            if failure_stage == "profile":
                raise ProviderError(message, transient=False)
            return TextResult(
                text=json.dumps(
                    {"locales": {"pt-BR": {"title": "Lia", "left": "Um", "right": "Dois"}}}
                )
            )

    class Images:
        async def generate_scene(self, **kwargs):
            raise ProviderError(message, transient=False)

    monkeypatch.setattr(settings, "offline_fallback", False)
    monkeypatch.setattr(settings, "skip_openai", False)
    monkeypatch.setattr(handlers, "get_text_provider", lambda *a: Text())
    monkeypatch.setattr(handlers, "get_image_provider", lambda *a: Images())
    response = client.post(f"/v1/projects/{pid}/preview", json={})
    assert response.status_code == 202
    job = db.get(Job, uuid.UUID(response.json()["job_id"]))
    await runner.process_job(db, job)
    db.expire_all()
    project = db.get(Project, uuid.UUID(pid))
    assert job.status == "FAILED"
    assert not project.book_profile.get("credits_fallback")
    assert project.book_profile["stage"] == "ficha"
    assert project.character_approved_at is None and project.book_approved_at is None
    assert not (project.purchase_flow or {}).get("preview_approved_at")
    assert len(db.scalars(select(Job).where(Job.project_id == project.id)).all()) == 1
    assert client.get(f"/v1/projects/{pid}/assets").json()["previews"] == []


@pytest.mark.asyncio
async def test_explicit_rehearsal_still_requires_each_approval(studio, monkeypatch):
    from fastapi import HTTPException

    from app.services import purchase_flow

    client, db, pid, _ = studio
    monkeypatch.setattr(settings, "offline_fallback", False)
    monkeypatch.setattr(settings, "skip_openai", True)
    await _run(studio, "preview")
    project = db.get(Project, uuid.UUID(pid))
    assert project.book_profile["stage"] == "preview_ready"
    with pytest.raises(HTTPException):
        purchase_flow.require_paid(db, project)
    assert not db.scalar(select(Job).where(Job.project_id == project.id, Job.type == "STORY"))
    await _run(studio, "story")
    db.expire_all()
    assert project.book_profile["stage"] == "story_ready"
    assert not (project.purchase_flow or {}).get("preview_approved_at")
    assert not db.scalar(select(Job).where(Job.project_id == project.id, Job.type == "AVATAR"))


def _sixteen(title: str = "Lia") -> str:
    return f"Título: {title}\n\n" + "\n\n".join(f"Página {i}:\nVerso {i}." for i in range(1, 17))


@pytest.mark.asyncio
async def test_page_correction_keeps_the_story_while_ai_is_paused(studio, monkeypatch):
    client, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    original = _sixteen()
    book_profile.update(
        project,
        stage="story_ready",
        costume="azul",
        locales={"pt-BR": {"title": "Lia"}},
        stories={"pt-BR": original},
    )
    project.story_text = original
    db.commit()
    monkeypatch.setattr(settings, "offline_fallback", False)
    monkeypatch.setattr(settings, "skip_openai", True)
    response = client.post(f"/v1/projects/{pid}/story", json={"page": 3, "brief": "Mais luz"})
    assert response.status_code == 202, response.text
    job = db.get(Job, uuid.UUID(response.json()["job_id"]))
    await runner.process_job(db, job)
    db.expire_all()
    assert job.status == "FAILED"
    assert "pausada" in (job.error or "")
    assert project.story_text == original
    assert "Verso 3." in project.book_profile["stories"]["pt-BR"]
    assert not project.book_profile.get("page_revisions")
    assert project.status == "STORY_READY"


@pytest.mark.asyncio
async def test_page_correction_rewrites_only_the_asked_page(studio, monkeypatch):
    client, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    original = _sixteen()
    book_profile.update(
        project,
        stage="story_ready",
        costume="azul",
        locales={"pt-BR": {"title": "Lia"}},
        stories={"pt-BR": original},
    )
    project.story_text = original
    db.commit()

    class Text:
        async def generate_story(self, **kwargs):
            assert kwargs["pages"] == 1
            assert (
                "Pedido do adulto, que não pode ser copiado como texto da página: Mais luz"
                in kwargs["brief"]
            )
            assert "Verso 3." in kwargs["brief"]
            return TextResult(text="Lia acendeu três estrelas.", cost_usd=0, meta={})

        async def moderate_book_input(self, **kwargs):
            return TextResult(text='{"flagged":false}', cost_usd=0, meta={"flagged": False})

    monkeypatch.setattr(settings, "offline_fallback", False)
    monkeypatch.setattr(settings, "skip_openai", False)
    monkeypatch.setattr(handlers, "get_text_provider", lambda *a, **k: Text())
    response = client.post(f"/v1/projects/{pid}/story", json={"page": 3, "brief": "Mais luz"})
    assert response.status_code == 202, response.text
    job = db.get(Job, uuid.UUID(response.json()["job_id"]))
    await runner.process_job(db, job)
    db.expire_all()
    text = project.book_profile["stories"]["pt-BR"]
    assert job.status == "DONE"
    assert "Lia acendeu três estrelas." in text
    assert "Verso 1." in text and "Verso 2." in text and "Verso 4." in text
    assert "Verso 3." not in text
    assert project.book_profile["page_revisions"]["pt-BR"]["3"] == "Verso 3."


def test_undo_restores_the_changed_story_page(studio):
    client, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    changed = _sixteen().replace("Verso 3.", "Lia acendeu três estrelas.")
    book_profile.update(
        project,
        stage="story_ready",
        locales={"pt-BR": {"title": "Lia"}},
        stories={"pt-BR": changed},
        page_revisions={"pt-BR": {"3": "Verso 3."}},
    )
    project.story_text = changed
    db.commit()
    response = client.post(f"/v1/projects/{pid}/story/page-undo", json={"page": 3})
    assert response.status_code == 200, response.text
    db.expire_all()
    text = project.book_profile["stories"]["pt-BR"]
    assert "Verso 3." in text
    assert "Lia acendeu três estrelas." not in text
    assert "Verso 1." in text and "Verso 4." in text
    assert not (project.book_profile.get("page_revisions") or {})
    assert project.story_text == text
    again = client.post(f"/v1/projects/{pid}/story/page-undo", json={"page": 3})
    assert again.status_code == 409


@pytest.mark.asyncio
async def test_story_provider_error_never_approves_or_enqueues_avatar(studio, monkeypatch):
    client, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    book_profile.update(
        project, stage="preview_ready", costume="azul", locales={"pt-BR": {"title": "Lia"}}
    )
    db.commit()

    class Text:
        async def generate_story(self, **kwargs):
            raise ProviderError("OpenAI 429: insufficient_quota", transient=False)

        async def moderate_book_input(self, **kwargs):
            return TextResult(text='{"flagged":false}', cost_usd=0, meta={"flagged": False})

    monkeypatch.setattr(settings, "offline_fallback", False)
    monkeypatch.setattr(settings, "skip_openai", False)
    monkeypatch.setattr(handlers, "get_text_provider", lambda *a: Text())
    response = client.post(f"/v1/projects/{pid}/story", json={})
    job = db.get(Job, uuid.UUID(response.json()["job_id"]))
    await runner.process_job(db, job)
    db.expire_all()
    assert job.status == "FAILED"
    assert project.book_profile["stage"] == "preview_ready"
    assert project.story_text is None
    assert not db.scalar(select(Job).where(Job.project_id == project.id, Job.type == "AVATAR"))


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
        async def moderate_book_input(self, *, text, photos):
            assert photos == [_png()]
            return TextResult(
                text='{"flagged": false}',
                cost_usd=0,
                meta={"flagged": False, "model": "omni-moderation-latest"},
            )

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
    from app.ai_clients.text_openai import OpenAITextProvider

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

    async def moderate_book_input(self, **kwargs):
        return TextResult(
            text='{"flagged": false}',
            cost_usd=0,
            meta={"flagged": False, "model": "omni-moderation-latest"},
        )

    monkeypatch.setattr(OpenAITextProvider, "moderate_book_input", moderate_book_input)
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


def test_pending_checkout_can_refine_title_without_changing_payment_or_delivery(
    studio, monkeypatch
):
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
    assert {
        column.name: getattr(order, column.name) for column in order.__table__.columns
    } == before
    assert project.book_profile["title"] == "Lia na Lua"
    assert project.book_profile["stage"] == "preview_approved"
    order.payment_status = "paid"
    db.commit()
    assert (
        client.put(f"/v1/projects/{pid}/preview/title", json={"title": "Outro"}).status_code == 409
    )


@pytest.mark.parametrize("stage", ["preview_ready", "story_ready", "story_approved"])
def test_preview_adjustments_accept_all_preapproval_review_stages(studio, stage):
    client, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    book_profile.update(project, stage=stage, stories={"pt-BR": "História anterior"})
    db.commit()
    response = client.put(
        f"/v1/projects/{pid}/preview/changes",
        json={
            "title": "Lia e as estrelas",
            "theme_description": "Aventura espacial",
            "photo_notes": "Mais estrelas na capa",
            "story_text": "",
        },
    )
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
    response = client.put(
        f"/v1/projects/{pid}/preview/changes",
        json={
            "title": "Lia",
            "theme_description": "Aventura",
            "photo_notes": "Mais luz",
        },
    )
    assert response.status_code == 409
    db.refresh(project)
    assert project.book_profile["stage"] == "story_approved"


def test_fallback_book_requires_regeneration_and_preserves_archived_material(studio):
    client, db, pid, store = studio
    project = db.get(Project, uuid.UUID(pid))
    book_profile.update(project, credits_fallback=True, stage="book_ready", current_page=16)
    project.story_text = "História anterior de contingência"
    project.ebook_url = "old-book.pdf"
    project.purchase_flow = {"full_book_ready_at": "2026-10-30", "stage": "book_ready"}
    asset = Asset(
        project_id=project.id,
        kind="page_image",
        storage_key="old-page.png",
        meta={"workflow": 1, "role": "com_texto", "page": 1},
    )
    db.add(asset)
    store["old-page.png"] = _png()
    db.commit()
    for path in (
        "preview/approve",
        "story/approve",
        "avatar/approve",
        "book/approve",
        "pages/next",
    ):
        assert client.post(f"/v1/projects/{pid}/{path}", json={}).status_code == 409
    response = client.post(f"/v1/projects/{pid}/preview/retry-ai")
    assert response.status_code == 202, response.text
    db.refresh(project)
    db.refresh(asset)
    assert project.book_profile["stage"] == "ficha"
    assert project.book_profile["current_page"] == 0
    assert project.book_profile["credits_fallback"] is False
    assert project.book_profile["fallback_archive"]["ebook_url"] == "old-book.pdf"
    assert (
        project.book_profile["fallback_archive"]["story_text"]
        == "História anterior de contingência"
    )
    assert asset.meta["archived_fallback"] is True and asset.meta["workflow"] == 0
    assert store["old-page.png"]
    assert not project.purchase_flow["preview_approved_at"]
    assert not project.purchase_flow["full_book_ready_at"]
    job = db.get(Job, uuid.UUID(response.json()["job_id"]))
    assert job.result["payload"]["master_preview"] is True


@pytest.mark.asyncio
async def test_project_test_mode_costs_zero_and_waits_at_every_review(studio, monkeypatch):
    from app.models import JobType
    from app.printkit.service import get_print_order
    from app.services import jobs as jobs_service
    from app.services import purchase_flow

    client, db, pid, store = studio

    class NoAI:
        def __getattr__(self, name):
            raise AssertionError(f"Test mode called AI: {name}")

    monkeypatch.setattr(settings, "offline_fallback", False)
    monkeypatch.setattr(settings, "skip_openai", False)
    monkeypatch.setattr(settings, "credits_enabled", True)
    monkeypatch.setattr(handlers, "get_text_provider", lambda *a: NoAI())
    monkeypatch.setattr(handlers, "get_image_provider", lambda *a: NoAI())
    response = client.post(f"/v1/projects/{pid}/preview/test")
    assert response.status_code == 202, response.text
    preview = db.get(Job, uuid.UUID(response.json()["job_id"]))
    await runner.process_job(db, preview)
    db.expire_all()
    project = db.get(Project, uuid.UUID(pid))
    assert preview.status == "DONE", preview.error
    assert preview.cost_credits == 0 and not preview.cost_usd
    assert project.book_profile["test_mode"] is True
    assert project.book_profile["stage"] == "preview_ready"
    assert len(client.get(f"/v1/projects/{pid}/assets").json()["previews"]) == 3
    assert not db.scalar(select(Job).where(Job.project_id == project.id, Job.type == "STORY"))
    assert not (project.purchase_flow or {}).get("preview_approved_at")
    await _run(studio, "story")
    assert project.book_profile["test_preview_approved_at"]
    assert project.book_profile["stage"] == "story_ready"
    assert not db.scalar(select(Job).where(Job.project_id == project.id, Job.type == "AVATAR"))
    assert client.post(f"/v1/projects/{pid}/story/approve").status_code == 200
    assert client.post(f"/v1/projects/{pid}/preview/approve").status_code == 200
    order = get_print_order(db, project.id)
    order.payment_status = "paid"
    db.commit()
    avatar = purchase_flow.enqueue_paid_book(db, order)
    await runner.process_job(db, avatar)
    db.expire_all()
    assert avatar.status == "DONE", avatar.error
    assert project.book_profile["stage"] == "avatar_ready"
    assert project.character_approved_at is None
    assert client.post(f"/v1/projects/{pid}/pages/next", json={}).status_code == 409
    assert client.post(f"/v1/projects/{pid}/avatar/approve").status_code == 200
    page = jobs_service.enqueue_job(
        db,
        user=project.user,
        project=project,
        job_type=JobType.EBOOK,
        payload={"master_page": True, "page": 1, "purchase_full_book": True},
    )
    await runner.process_job(db, page)
    db.expire_all()
    assert page.status == "DONE", page.error
    assert project.book_profile["stage"] == "page_ready"
    assert project.book_profile["current_page"] == 1
    assert not db.scalar(select(Job).where(Job.project_id == project.id, Job.status == "PENDING"))
    assert all(
        job.cost_credits == 0 and not job.cost_usd
        for job in db.scalars(select(Job).where(Job.project_id == project.id))
    )
    assert store


@pytest.mark.asyncio
async def test_global_pause_covers_new_requests_and_cannot_be_disabled_by_retry(
    studio, monkeypatch
):
    client, db, pid, _ = studio
    monkeypatch.setattr(settings, "offline_fallback", False)
    monkeypatch.setattr(settings, "skip_openai", True)
    monkeypatch.setattr(settings, "credits_enabled", True)

    class NoAI:
        def __getattr__(self, name):
            raise AssertionError(f"Global pause called AI: {name}")

    monkeypatch.setattr(handlers, "get_text_provider", lambda *a: NoAI())
    monkeypatch.setattr(handlers, "get_image_provider", lambda *a: NoAI())
    preview = await _run(studio, "preview")
    assert preview.cost_credits == 0 and not preview.cost_usd
    state = client.get(f"/v1/projects/{pid}").json()
    assert state["test_mode"] is True and state["ai_generation_paused"] is True
    assert state["book_profile"]["stage"] == "preview_ready"
    assert not db.scalar(select(Job).where(Job.project_id == uuid.UUID(pid), Job.type == "STORY"))
    assert client.post(f"/v1/projects/{pid}/preview/title-suggestions", json={}).status_code == 409
    response = client.post(f"/v1/projects/{pid}/preview/retry-ai")
    assert response.status_code == 202, response.text
    db.expire_all()
    project = db.get(Project, uuid.UUID(pid))
    assert project.book_profile["test_mode"] is True
    retry = db.get(Job, uuid.UUID(response.json()["job_id"]))
    assert retry.cost_credits == 0


@pytest.mark.asyncio
async def test_global_pause_blocks_paid_video_and_voice_providers(monkeypatch):
    from app.ai_clients.video_kling import KlingVideoProvider
    from app.media.tts import TtsError, clone_voice, elevenlabs_configured, get_tts_provider

    monkeypatch.setattr(settings, "skip_openai", True)
    monkeypatch.setattr(settings, "elevenlabs_api_key", "configured-but-paused")
    assert elevenlabs_configured() is False
    with pytest.raises(TtsError):
        get_tts_provider()
    with pytest.raises(TtsError):
        await clone_voice("Teste", b"fake", "voice.mp3")
    with pytest.raises(ProviderError):
        await KlingVideoProvider().create_video(image=b"fake", prompt="test", duration_s=5)


@pytest.mark.asyncio
async def test_editorial_preview_three_independent_scenes_and_cover_retry(studio):
    from app.services import editorial_profile

    client, db, pid, store = studio
    project = db.get(Project, uuid.UUID(pid))
    book_profile.update(
        project,
        editorial=editorial_profile.snapshot("2026-11-04.1"),
        languages=["pt-BR"],
        title="ANdré no Computador",
    )
    db.commit()
    job = await _run(studio, "preview")
    assert job.result["preview_complete"] is True
    assets = client.get(f"/v1/projects/{pid}/assets").json()["previews"]
    assert len(assets) == 3
    assert project.book_profile["editorial"] == editorial_profile.snapshot()
    assert project.book_profile["locales"]["pt-BR"]["title"] == "ANdré no Computador"
    assert len(job.result["scenes"]) == 3
    assert not db.scalar(select(Job).where(Job.project_id == project.id, Job.type == "STORY"))
    # Demo images are never downloadable as validated personalized output.
    assert client.get(f"/v1/projects/{pid}/preview/package").status_code == 409
    before = {a["role"]: a["url"] for a in assets if a["language"] == "pt-BR"}
    await _run(studio, "preview", {"image": "01_CAPA", "language": "pt-BR"})
    after = {
        a["role"]: a["url"]
        for a in client.get(f"/v1/projects/{pid}/assets").json()["previews"]
        if a["language"] == "pt-BR"
    }
    assert before["02_LIVRO_ABERTO"] == after["02_LIVRO_ABERTO"]
    assert before["03_LEITURA"] != after["03_LEITURA"]


def test_editorial_references_select_only_requested_finish():
    from app.services import editorial_profile

    realistic = editorial_profile.references("realistic")
    cartoon = editorial_profile.references("cartoon")
    realistic_art = editorial_profile.references("realistic", art_only=True)
    assert any("acabamento-amor" in path for path, _ in realistic)
    assert not any("acabamento-amor" in path for path, _ in cartoon)
    assert sum("cartoon-style" in path for path, _ in cartoon) == 2
    assert len(realistic_art) == 1
    assert not any("texto-" in path or "titulo-" in path for path, _ in realistic_art)
    for _, data in realistic + cartoon:
        Image.open(io.BytesIO(data)).verify()


def test_current_editorial_art_prompt_reserves_text_for_exact_composition(studio):
    from app.services import editorial_profile

    _, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    book_profile.update(
        project,
        editorial=editorial_profile.snapshot("2026-11-04.4"),
        locales={
            "pt-BR": {
                "title": "ANdré no Computador",
                "left": "André aprende com alegria.",
                "right": "Uma descoberta a cada dia.",
            }
        },
    )

    cover_art = editorial_profile.prompt(project, "pt-BR", "01_CAPA", include_text=False)
    spread_art = editorial_profile.prompt(project, "pt-BR", "02_LIVRO_ABERTO", include_text=False)
    cover_validation = editorial_profile.prompt(project, "pt-BR", "01_CAPA")
    spread_validation = editorial_profile.prompt(project, "pt-BR", "02_LIVRO_ABERTO")

    assert "ANdré no Computador" not in cover_art
    assert "ANdré no Computador" not in spread_art
    spread_data = json.loads(spread_art.split("DADOS DO LIVRO:\n", 1)[1])
    assert spread_data["texts"] == {}
    assert spread_data["illustration_guidance"]["left_page_action"] == "André aprende com alegria."
    assert spread_data["illustration_guidance"]["right_page_action"] == "Uma descoberta a cada dia."
    assert "do not render" in spread_data["illustration_guidance"]["instruction"]
    assert "SEM TIPOGRAFIA" in cover_art
    assert "SEM TIPOGRAFIA" in spread_art
    assert "LEITURA" not in spread_art
    assert "ENTREGA" not in spread_art
    assert "três imagens" not in spread_art
    assert "segurando o livro" not in spread_art
    assert "texto-meu-pai" not in spread_art
    assert "titulo-amor-de-bisavo" not in spread_art
    assert "LIVRO ABERTO" not in cover_art
    assert "segurando o livro" not in cover_art
    assert "ANdré no Computador" in cover_validation
    assert "André aprende com alegria." in spread_validation
    assert "Uma descoberta a cada dia." in spread_validation


def test_editorial_validation_prompt_contains_only_the_current_scene_contract(studio):
    from app.services import editorial_profile
    from app.workers.handlers.master_book import _preview_validation_prompt

    _, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    book_profile.update(
        project,
        editorial=editorial_profile.snapshot("2026-11-04.4"),
        locales={
            "pt-BR": {
                "title": "Lia e as estrelas",
                "left": "Lia olha o céu.\nUma estrela a chamar.",
                "right": "Lia aprende a esperar.\nE o céu volta a brilhar.",
            }
        },
    )

    spread = _preview_validation_prompt(project, "pt-BR", "02_LIVRO_ABERTO")
    cover = _preview_validation_prompt(project, "pt-BR", "01_CAPA")

    assert "VALIDATION ROLE: 02_LIVRO_ABERTO" in spread
    assert "Lia olha o céu." in spread
    assert "Lia aprende a esperar." in spread
    assert "title must not appear" in spread
    assert "Lia e as estrelas" not in spread
    assert "VALIDATION ROLE: 01_CAPA" in cover
    assert "Lia e as estrelas" in cover
    assert "Lia olha o céu." not in cover


def test_assets_api_hides_previews_from_an_older_editorial_profile(studio):
    from app.services import editorial_profile

    client, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    old_profile = editorial_profile.snapshot("2026-11-04.1")
    book_profile.update(
        project,
        editorial=editorial_profile.snapshot(),
        languages=["pt-BR"],
    )
    db.add(
        Asset(
            project_id=project.id,
            kind=AssetKind.COVER.value,
            storage_key="old-profile-cover.png",
            meta={
                "workflow": 1,
                "language": "pt-BR",
                "role": "01_CAPA",
                "editorial": old_profile,
                "validation": {"status": "valid"},
            },
        )
    )
    db.commit()

    assert client.get(f"/v1/projects/{pid}/assets").json()["previews"] == []


@pytest.mark.asyncio
async def test_editorial_provider_references_resume_and_zip(studio, monkeypatch):
    from app.services import editorial_profile

    monkeypatch.setattr(editorial_profile, "CURRENT_VERSION", "2026-11-04.4")

    client, db, pid, store = studio
    project = db.get(Project, uuid.UUID(pid))
    book_profile.update(
        project,
        editorial=editorial_profile.snapshot(),
        languages=["pt-BR"],
        locales={
            lang: {
                "title": "ANdré no Computador",
                "left": "André aprende com alegria.",
                "right": "Uma descoberta a cada dia.",
            }
            for lang in ["pt-BR"]
        },
    )
    db.commit()
    calls = []
    generated = []

    class Images:
        async def generate_scene(self, **kwargs):
            calls.append(kwargs)
            if len(calls) == 3:
                raise ProviderError("provider unavailable", transient=False)
            out = io.BytesIO()
            Image.new("RGB", (1024, 1024), (len(calls) * 15, 120, 160)).save(out, "PNG")
            image = out.getvalue()
            generated.append(image)
            return ImageResult(image, cost_usd=0)

    class Text:
        async def moderate_book_input(self, **kwargs):
            return TextResult(
                text='{"flagged": false}',
                cost_usd=0,
                meta={"flagged": False, "model": "omni-moderation-latest"},
            )

        async def validate_editorial_preview(self, **kwargs):
            assert kwargs["photos"][0] == _png()
            return TextResult(
                text='{"valid": true, "issues": [], "limitations": ["mock inspection"]}', cost_usd=0
            )

    monkeypatch.setattr(settings, "offline_fallback", False)
    monkeypatch.setattr(handlers, "get_image_provider", lambda: Images())
    monkeypatch.setattr(handlers, "get_text_provider", lambda: Text())
    response = client.post(f"/v1/projects/{pid}/preview")
    failed = db.get(Job, uuid.UUID(response.json()["job_id"]))
    await runner.process_job(db, failed)
    assert failed.status == "FAILED"
    assert len(client.get(f"/v1/projects/{pid}/assets").json()["previews"]) == 2
    assert calls[0]["reference_role"] == "character"
    assert "LEITURA" not in calls[0]["prompt"]
    assert calls[1]["character_ref"] == _png()
    assert calls[1]["reference_role"] == "character"
    assert generated[0] not in calls[1]["extra_refs"]  # capa não induz letras no miolo
    assert "LEITURA" not in calls[1]["prompt"]
    assert "segurando o livro" not in calls[1]["prompt"]
    assert "a capa não é referência desta cena" in calls[1]["prompt"]
    assert "sem qualquer letra, palavra" in calls[1]["prompt"]
    assert "Uma descoberta a cada dia." in calls[1]["prompt"]
    assert calls[2]["reference_role"] == "cover"
    assert "CENA ÚNICA" in calls[2]["prompt"]
    await _run(studio, "preview", key="resume-editorial")
    assert len(calls) == 4  # three outputs plus exactly one failed call
    assert all(c["photo"] == _png() and len(c["extra_refs"]) >= 2 for c in calls)
    final_assets = db.scalars(select(Asset).where(Asset.project_id == uuid.UUID(pid))).all()
    editorial_assets = [
        asset
        for asset in final_assets
        if (asset.meta or {}).get("workflow") == 1
        and (asset.meta or {}).get("language") == "pt-BR"
        and (asset.meta or {}).get("role") in editorial_profile.ROLES
    ]
    assert len(editorial_assets) == 3
    for asset in editorial_assets:
        image = Image.open(io.BytesIO(store[asset.storage_key]))
        colors = len(image.getcolors(maxcolors=2_000_000))
        if asset.meta["role"] == "03_LEITURA":
            assert colors == 1
        else:
            assert colors > 1
    response = client.get(f"/v1/projects/{pid}/preview/package")
    assert response.status_code == 200
    import zipfile

    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert len(archive.namelist()) == 3
        for name in archive.namelist():
            Image.open(io.BytesIO(archive.read(name))).verify()

    await _run(
        studio, "preview", {"image": "01_CAPA", "language": "pt-BR"}, key="refresh-cover-editorial"
    )
    assert len(client.get(f"/v1/projects/{pid}/assets").json()["previews"]) == 3
    assert client.get(f"/v1/projects/{pid}/preview/package").status_code == 200


@pytest.mark.asyncio
async def test_input_safety_block_is_cached_and_stops_before_any_paid_generation(
    studio, monkeypatch
):
    from app.workers.handlers.master_book import _preflight_input_safety

    client, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    job = Job(project_id=project.id, type="EBOOK", status="RUNNING", cost_usd=0)
    project.story_text = "Página 1: uma história personalizada"
    job.result = {"payload": {"adjustment": "inclua uma ponte azul"}}
    db.add(job)
    db.commit()
    monkeypatch.setattr(settings, "offline_fallback", False)
    monkeypatch.setattr(settings, "skip_openai", False)
    calls = []

    class Text:
        async def moderate_book_input(self, *, text, photos):
            calls.append((text, photos))
            return TextResult(
                text='{"flagged": true}',
                cost_usd=0,
                meta={"flagged": True, "model": "omni-moderation-latest"},
            )

    monkeypatch.setattr(handlers, "get_text_provider", lambda: Text())
    with pytest.raises(ProviderError, match="INPUT_SAFETY_BLOCKED"):
        await _preflight_input_safety(db, job, project, [_png()])
    with pytest.raises(ProviderError, match="INPUT_SAFETY_BLOCKED"):
        await _preflight_input_safety(db, job, project, [_png()])
    next_job = Job(
        project_id=project.id,
        type="EBOOK",
        status="RUNNING",
        cost_usd=0,
        result={"payload": {"adjustment": "inclua uma ponte azul"}},
    )
    db.add(next_job)
    db.commit()
    with pytest.raises(ProviderError, match="INPUT_SAFETY_BLOCKED"):
        await _preflight_input_safety(db, next_job, project, [_png()])

    assert len(calls) == 1
    assert "história personalizada" in calls[0][0]
    assert "ponte azul" in calls[0][0]
    assert calls[0][1] == [_png()]
    assert job.result["input_safety"]["status"] == "blocked"
    assert job.cost_usd == 0
    response = client.get(f"/v1/projects/{pid}").json()
    assert "input_safety_checks" not in response["book_profile"]


@pytest.mark.asyncio
async def test_editorial_stage_blocks_same_input_after_unknown_provider_outcome(composed_studio):
    from app.workers.handlers.editorial_book import Pipeline, signature

    studio, _, _ = composed_studio
    _, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    job = Job(project_id=project.id, type="EBOOK", status="RUNNING", cost_usd=0)
    db.add(job)
    db.commit()
    pipeline = Pipeline(db, job, project, [_png()])
    name = "cover:art"
    inputs = {"attempt": "unknown-outcome-guard-test"}
    key = f"editorial/{project.id}/{signature([pipeline.base, name, inputs])}.png"
    pipeline._remember_unknown_generation(
        key,
        ProviderError(
            "response timed out",
            transient=True,
            retry_safe=False,
            outcome_unknown=True,
            client_request_id="request-guard-test",
        ),
        stage=name,
    )
    called = False

    async def must_not_generate(_attempt):
        nonlocal called
        called = True
        return _png(), {}

    with pytest.raises(ProviderError, match="GENERATION_OUTCOME_UNKNOWN"):
        await pipeline.stage(name, inputs, must_not_generate)
    assert called is False


@pytest.mark.asyncio
async def test_editorial_preview_fails_closed_when_validation_reports_any_issue(
    studio, monkeypatch
):
    from app.services import editorial_profile

    monkeypatch.setattr(editorial_profile, "CURRENT_VERSION", "2026-11-04.4")

    client, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    book_profile.update(
        project,
        editorial=editorial_profile.snapshot(),
        languages=["pt-BR"],
        locales={
            "pt-BR": {
                "title": "Lia e as estrelas",
                "left": "Lia olha o céu.",
                "right": "Juntas brilham as estrelas.",
            }
        },
    )
    db.commit()

    class Images:
        async def generate_scene(self, **kwargs):
            return ImageResult(_png(), cost_usd=0)

    class Text:
        async def moderate_book_input(self, **kwargs):
            return TextResult(
                text='{"flagged": false}',
                cost_usd=0,
                meta={"flagged": False, "model": "omni-moderation-latest"},
            )

        async def validate_editorial_preview(self, **kwargs):
            return TextResult(
                text='{"valid": true, "issues": ["título duplicado"], "limitations": []}',
                cost_usd=0,
            )

    monkeypatch.setattr(settings, "offline_fallback", False)
    monkeypatch.setattr(handlers, "get_image_provider", lambda: Images())
    monkeypatch.setattr(handlers, "get_text_provider", lambda: Text())
    response = client.post(f"/v1/projects/{pid}/preview")
    job = db.get(Job, uuid.UUID(response.json()["job_id"]))
    await runner.process_job(db, job)

    assert job.status == "FAILED"
    assert "título duplicado" in job.error
    assert len(client.get(f"/v1/projects/{pid}/assets").json()["previews"]) == 0
    db.refresh(project)
    assert (project.purchase_flow or {}).get("preview_ready_at") is None


@pytest.mark.parametrize(
    "title", ["MEU PAI, MEU HERÓI!", "Mako, Meu Amigo Fiel!", "AMOR DE AVÔ, MEU PORTO SEGURO"]
)
def test_vibrant_cover_title_fits_full_width_without_changing_literal_copy(title):
    from app.services import editorial_profile
    from app.workers import editorial_render as render

    profile = {"editorial": editorial_profile.snapshot()}
    _, heading = render.text(_png(), title, profile, title=True)
    assert " ".join(heading["lines"]) == title
    assert len(heading["lines"]) == 2
    assert heading["color"] == "#00245D"
    assert heading["weight"] == 900
    assert heading["alignment"] == "center"
    assert heading["region"] == [0.06, 0.045, 0.94, 0.29]
    assert editorial_profile.policy(profile)["visual"]["color"] == "vibrant_balanced_natural_skin"


@pytest.mark.asyncio
async def test_current_preview_checks_cover_and_source_art_without_extra_image_calls(
    reference_studio, monkeypatch
):
    from app.services import editorial_profile

    studio, calls, _ = reference_studio
    client, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    monkeypatch.setattr(editorial_profile, "CURRENT_VERSION", "2026-11-05.3")
    book_profile.update(project, editorial=editorial_profile.snapshot())
    db.commit()
    text_class = type(handlers.get_text_provider())

    reviewed = []
    validate = text_class.validate_editorial_preview

    async def mandatory_contract_checks(self, **kwargs):
        reviewed.append(kwargs)
        return await validate(self, **kwargs)

    monkeypatch.setattr(text_class, "validate_editorial_preview", mandatory_contract_checks)
    job = await _run(studio, "preview", key="current-layout-all-reserve-repairs")
    assert job.status == "DONE", job.error
    repairs = [call for call in calls if call.get("operation") == "outpaint_reframed_art"]
    assert len(repairs) == 0
    assert len(calls) == 4
    generated = [call for call in calls if "prompt" in call and not call.get("operation")]
    assert all("COMPOSITION EXAMPLES GUIDE" in call["prompt"] for call in generated[:3])
    assert sum(check["prompt"].startswith("ARTE_BASE:") for check in reviewed) == 3
    assert sum(check["prompt"].startswith("CAPA_PLANA:") for check in reviewed) == 1
    assert "desenha uma flor" in generated[0]["prompt"]
    assert "MANDATORY COVER FRAMING" in generated[0]["prompt"]
    assert "RECOMPOSE THE SCENE" in generated[0]["prompt"]
    assert "cast_contract" in reviewed[0]["full_image_prompt"]
    assert job.cost_credits == 0 and not job.cost_usd
    assert len(client.get(f"/v1/projects/{pid}/assets").json()["previews"]) == 3
    db.refresh(project)
    assert not (project.purchase_flow or {}).get("preview_approved_at")


@pytest.mark.asyncio
async def test_current_preview_is_delivered_for_explicit_user_approval(reference_studio):
    studio, calls, control = reference_studio
    client, db, pid, _ = studio
    response = client.post(f"/v1/projects/{pid}/preview")
    job = db.get(Job, uuid.UUID(response.json()["job_id"]))
    await runner.process_job(db, job)
    assert job.status == "DONE", job.error
    assert len(calls) == 4
    project = db.get(Project, uuid.UUID(pid))
    assert not (project.purchase_flow or {}).get("preview_approved_at")
    scenes = db.scalars(
        select(Asset).where(
            Asset.project_id == uuid.UUID(pid), Asset.kind.in_(["cover", "page_image", "in_hand"])
        )
    ).all()
    assert len(scenes) == 3
    for scene in scenes:
        if scene.kind == "cover":
            assert scene.meta["validation"]["status"] == "valid"
            assert (
                scene.meta["layout"]["title_clearance"]["method"] == "mandatory_visual_title_review"
            )
            assert scene.meta["layout"]["title_clearance"]["status"] == "valid"
        else:
            assert scene.meta["validation"] == {
                "status": "awaiting_user_review",
                "reviewer": "user",
                "method": "technical_integrity_only",
            }
    assert client.get(f"/v1/projects/{pid}/preview/package").status_code == 200
    # Merely claiming a pending review is insufficient without server provenance.
    original_meta = scenes[0].meta
    scenes[0].meta = {**original_meta, "validation": {"status": "awaiting_user_review"}}
    db.commit()
    assert client.get(f"/v1/projects/{pid}/preview/package").status_code == 409
    scenes[0].meta = original_meta
    db.commit()
    assert client.post(f"/v1/projects/{pid}/preview/approve").status_code == 200
    db.refresh(project)
    assert project.purchase_flow["preview_approved_at"]


@pytest.mark.asyncio
async def test_current_cover_rejection_stops_without_automatic_image_retry(reference_studio):
    studio, calls, control = reference_studio
    control["reject"] = True
    client, db, pid, _ = studio
    response = client.post(
        f"/v1/projects/{pid}/preview", headers={"Idempotency-Key": "reject-wrong-cover"}
    )
    job = db.get(Job, uuid.UUID(response.json()["job_id"]))
    await runner.process_job(db, job)
    assert job.status == "FAILED"
    assert len(calls) == 1
    assert "reprovada" in job.error
    assert client.get(f"/v1/projects/{pid}/assets").json()["previews"] == []
    assert client.get(f"/v1/projects/{pid}/preview/package").status_code == 409
    assert not (db.get(Project, uuid.UUID(pid)).purchase_flow or {}).get("preview_ready_at")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "estimated_overlap,confirmed_overlap", [(True, False), (True, True), (False, True)]
)
async def test_cover_overlap_requires_visual_confirmation_and_cannot_bypass_review(
    reference_studio, monkeypatch, estimated_overlap, confirmed_overlap
):
    from app.workers import editorial_render as render

    studio, calls, control = reference_studio
    client, db, pid, _ = studio
    monkeypatch.setattr(
        render, "protected_heads", lambda _: [[0.3, 0.05, 0.8, 0.7]] if estimated_overlap else []
    )
    control["reject_cover_text_once"] = confirmed_overlap
    reviewed = []
    text_class = type(handlers.get_text_provider())
    validate = text_class.validate_editorial_preview

    async def visual_review(self, **kwargs):
        reviewed.append(kwargs)
        return await validate(self, **kwargs)

    monkeypatch.setattr(text_class, "validate_editorial_preview", visual_review)
    response = client.post(f"/v1/projects/{pid}/preview", json={"cover_only": True})
    job = db.get(Job, uuid.UUID(response.json()["job_id"]))
    await runner.process_job(db, job)
    assert job.status == ("FAILED" if confirmed_overlap else "DONE"), job.error
    assert len(calls) == 1
    assert any(check["prompt"].startswith("CAPA_PLANA:") for check in reviewed)
    assert reviewed[0]["inspection_region"]
    previews = client.get(f"/v1/projects/{pid}/assets").json()["previews"]
    if confirmed_overlap:
        assert previews == []
        assert "texto sobre o cabelo" in job.error
    else:
        clearance = previews[0]["layout"]["title_clearance"]
        assert clearance["status"] == "valid"
        assert clearance["local_estimate"]["possible_overlap"] is True


@pytest.mark.asyncio
async def test_explicit_new_cover_keeps_new_art_revision_separate_from_retry_cache(
    reference_studio,
):
    studio, calls, _ = reference_studio
    await _run(studio, "preview", {"cover_only": True}, key="original-cover")
    await _run(studio, "preview", {"image": "01_CAPA"}, key="explicit-new-cover")
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_reserve_collision_moves_only_text_and_keeps_original_pixels(
    reference_studio, monkeypatch
):
    from app.workers import editorial_render as render

    studio, calls, _ = reference_studio
    client, db, pid, store = studio
    text_class = type(handlers.get_text_provider())
    validate = text_class.validate_editorial_preview
    inspected = []

    async def crop_review(self, **kwargs):
        inspected.append(kwargs)
        if len(inspected) == 1:
            return TextResult(
                text=json.dumps(
                    {"valid": False, "issues": ["Visible hair and head in crop"], "limitations": []}
                ),
                cost_usd=0,
                meta={"review_scope": "text_reserve"},
            )
        return await validate(self, **kwargs)

    monkeypatch.setattr(text_class, "validate_editorial_preview", crop_review)
    job = await _run(studio, "preview", {"cover_only": True}, key="text-only-reserve")
    assert job.status == "DONE", job.error
    assert len(calls) == 1  # no replacement image, blur, extension, or resizing
    assert inspected[0]["data"] == inspected[1]["data"]
    assert inspected[0]["inspection_region"] != inspected[1]["inspection_region"]
    flat = db.get(Project, uuid.UUID(pid)).book_profile["cover_calibration"]["flat_meta"]
    assert flat["local_reading_layout"]["source_pixels_unchanged"] is True
    assert flat["art_sha256"] == render.digest(inspected[0]["data"])
    assert store[flat["art_key"]] == inspected[0]["data"]
    assert not (db.get(Project, uuid.UUID(pid)).purchase_flow or {}).get("preview_approved_at")


@pytest.mark.asyncio
async def test_reserve_exhaustion_is_bounded_and_retry_reuses_purchased_art(
    reference_studio, monkeypatch
):
    studio, calls, _ = reference_studio
    client, db, pid, _ = studio
    text_class = type(handlers.get_text_provider())
    validate = text_class.validate_editorial_preview
    reviewed = []
    reject = True

    async def crop_review(self, **kwargs):
        reviewed.append(kwargs)
        if reject:
            return TextResult(
                text=json.dumps({"valid": False, "issues": ["Head in reserve"], "limitations": []}),
                cost_usd=0,
                meta={"review_scope": "text_reserve"},
            )
        return await validate(self, **kwargs)

    monkeypatch.setattr(text_class, "validate_editorial_preview", crop_review)
    job = await _run(
        studio, "preview", {"cover_only": True}, key="no-space-first", expected="FAILED"
    )
    assert job.status == "FAILED" and len(calls) == 1
    assert len(reviewed) == 3
    assert len({check["data"] for check in reviewed}) == 1
    assert client.get(f"/v1/projects/{pid}/assets").json()["previews"] == []
    reject = False
    retry = await _run(studio, "preview", {"cover_only": True}, key="no-space-retry")
    assert retry.status == "DONE", retry.error
    assert len(calls) == 1
    assert reviewed[-2]["data"] == reviewed[0]["data"]
    assert not (db.get(Project, uuid.UUID(pid)).purchase_flow or {}).get("preview_approved_at")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "context_change", [None, "legacy_crop", "full_preview", "theme_description", "costume"]
)
async def test_legacy_failed_cover_recovers_original_not_repaired_band(
    reference_studio, monkeypatch, context_change
):
    studio, calls, _ = reference_studio
    _, db, pid, _ = studio
    text_class = type(handlers.get_text_provider())
    validate = text_class.validate_editorial_preview
    reject = True
    inspected = []

    async def crop_review(self, **kwargs):
        inspected.append(kwargs)
        if reject:
            return TextResult(
                text=json.dumps({"valid": False, "issues": ["Hair in reserve"], "limitations": []}),
                cost_usd=0,
                meta={"review_scope": "text_reserve"},
            )
        return await validate(self, **kwargs)

    monkeypatch.setattr(text_class, "validate_editorial_preview", crop_review)
    body = {} if context_change == "full_preview" else {"cover_only": True}
    job = await _run(studio, "preview", body, key="old-cover-first", expected="FAILED")
    assert job.status == "FAILED" and len(calls) == 1
    # Simulate a failure recorded before original-candidate persistence existed.
    for asset in db.scalars(select(Asset).where(Asset.kind == "editorial_candidate")).all():
        db.delete(asset)
    if context_change == "legacy_crop":
        for asset in db.scalars(select(Asset).where(Asset.kind == "editorial_rejected")).all():
            meta = dict(asset.meta)
            meta.pop("review_scope", None)
            meta.pop("role", None)
            meta["validation"] = {
                **meta["validation"],
                "limitations": ["Cannot judge outside the supplied crop"],
            }
            asset.meta = meta
    elif context_change in {"theme_description", "costume"}:
        book_profile.update(
            db.get(Project, uuid.UUID(pid)), **{context_change: "Changed user context"}
        )
    db.commit()
    reject = False
    retry = await _run(studio, "preview", body, key="old-cover-retry")
    assert retry.status == "DONE", retry.error
    assert len(calls) == (
        4
        if context_change == "full_preview"
        else 2
        if context_change in {"theme_description", "costume"}
        else 1
    )
    if context_change not in {"theme_description", "costume"}:
        assert inspected[3]["data"] == inspected[0]["data"]


@pytest.mark.asyncio
async def test_quality_rejection_after_reserve_repair_does_not_keep_moving_text(
    reference_studio, monkeypatch
):
    studio, calls, _ = reference_studio
    client, db, pid, _ = studio
    text_class = type(handlers.get_text_provider())
    validate = text_class.validate_editorial_preview
    inspected = []

    async def review(self, **kwargs):
        inspected.append(kwargs)
        if len(inspected) == 1:
            return TextResult(
                text=json.dumps({"valid": False, "issues": ["Head in crop"], "limitations": []}),
                cost_usd=0,
                meta={"review_scope": "text_reserve"},
            )
        if kwargs["prompt"].startswith("CAPA_PLANA:"):
            return TextResult(
                text=json.dumps(
                    {
                        "valid": False,
                        "issues": ["Faixa artificial interrompe o fundo natural"],
                        "limitations": [],
                    }
                ),
                cost_usd=0,
            )
        return await validate(self, **kwargs)

    monkeypatch.setattr(text_class, "validate_editorial_preview", review)
    job = await _run(
        studio, "preview", {"cover_only": True}, key="quality-remains-blocking", expected="FAILED"
    )
    assert job.status == "FAILED" and "Faixa artificial" in job.error
    assert len(calls) == 1 and len(inspected) == 3
    assert client.get(f"/v1/projects/{pid}/assets").json()["previews"] == []
    assert not (db.get(Project, uuid.UUID(pid)).purchase_flow or {}).get("preview_ready_at")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "report", ["not-json", "[]", '{"valid":true,"issues":["Identity differs"],"limitations":[]}']
)
async def test_invalid_or_inconsistent_review_never_approves_or_regenerates(
    reference_studio, monkeypatch, report
):
    studio, calls, _ = reference_studio
    client, db, pid, _ = studio
    text_class = type(handlers.get_text_provider())

    async def review(self, **kwargs):
        return TextResult(text=report, cost_usd=0)

    monkeypatch.setattr(text_class, "validate_editorial_preview", review)
    job = await _run(
        studio, "preview", {"cover_only": True}, key="invalid-review", expected="FAILED"
    )
    assert job.status == "FAILED" and len(calls) == 1
    assert client.get(f"/v1/projects/{pid}/assets").json()["previews"] == []
    assert not (db.get(Project, uuid.UUID(pid)).purchase_flow or {}).get("preview_ready_at")


@pytest.mark.asyncio
async def test_corrupt_candidate_blocks_retry_without_purchasing_replacement(
    reference_studio, monkeypatch
):
    studio, calls, control = reference_studio
    _, db, pid, store = studio
    control["reject"] = True
    first = await _run(
        studio, "preview", {"cover_only": True}, key="candidate-first", expected="FAILED"
    )
    assert first.status == "FAILED" and len(calls) == 1
    candidate = db.scalar(select(Asset).where(Asset.kind == "editorial_candidate"))
    store[candidate.storage_key] = b"corrupt"
    control["reject"] = False
    retry = await _run(
        studio, "preview", {"cover_only": True}, key="candidate-corrupt-retry", expected="FAILED"
    )
    assert retry.status == "FAILED" and "Arte original armazenada inválida" in retry.error
    assert len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("version", ["2026-11-05.2", "2026-11-05.3"])
async def test_reference_pages_preserve_full_bleed_art_without_added_paper_margins(
    reference_studio, monkeypatch, version
):
    from app.services import editorial_profile
    from app.workers import editorial_render as render

    studio, calls, _ = reference_studio
    _, db, pid, store = studio
    project = db.get(Project, uuid.UUID(pid))
    monkeypatch.setattr(editorial_profile, "CURRENT_VERSION", version)
    book_profile.update(project, editorial=editorial_profile.snapshot())
    db.commit()
    job = await _run(studio, "preview", key="full-bleed-identity")
    assert job.status == "DONE", job.error
    assert len(calls) == 4  # three arts and the optional holding image
    sources = db.scalars(
        select(Asset).where(Asset.project_id == uuid.UUID(pid), Asset.kind == "editorial_source")
    ).all()
    for index, stage in enumerate(("cover", "preview:left", "preview:right"), start=1):
        art = next(a for a in sources if a.meta.get("stage") == stage + ":art")
        composed = next(a for a in sources if a.meta.get("stage") == stage + ":text")
        source = Image.open(io.BytesIO(store[art.storage_key])).convert("RGB")
        expected = Image.new("RGB", (1024, 1024), (index * 20, 120, 160))
        assert source.tobytes() == expected.tobytes()  # every original pixel survives
        assert art.meta["page_composition"]["method"] == "full_bleed_text_overlay"
        assert art.meta["page_composition"]["scale"] == 1
        assert composed.meta["art_sha256"] == render.digest(store[art.storage_key])
        final = Image.open(io.BytesIO(store[composed.storage_key])).convert("RGB")
        for corner in ((0, 0), (1023, 0), (0, 1023), (1023, 1023)):
            assert final.getpixel(corner) == expected.getpixel(corner)
        assert "separate ivory reading area" not in calls[index - 1]["prompt"]
        assert "this image IS the entire printed page" in calls[index - 1]["prompt"]
    assert not (project.purchase_flow or {}).get("preview_approved_at")


@pytest.mark.asyncio
async def test_technical_render_failure_is_not_reported_as_visual_rejection(reference_studio):
    from app.workers.handlers.editorial_book import Pipeline

    studio, _, _ = reference_studio
    client, db, pid, _ = studio
    response = client.post(f"/v1/projects/{pid}/preview")
    job = db.get(Job, uuid.UUID(response.json()["job_id"]))
    pipe = Pipeline(db, job, db.get(Project, uuid.UUID(pid)), [_png()])
    calls = []

    async def missing_surface(attempt):
        calls.append(attempt)
        raise ValueError("Book surface not identified")

    with pytest.raises(ProviderError, match="Book surface not identified") as failed:
        await pipe.stage("reading", {}, missing_surface)
    assert failed.value.transient is False
    assert "reprovada" not in str(failed.value)
    assert "Falha técnica" in str(failed.value)
    assert calls == [1]
    assert job.result["editorial_tasks"]["reading"]["detail"] == "Book surface not identified"


@pytest.mark.asyncio
async def test_retry_reuses_matching_generated_template_without_new_image_charge(
    reference_studio, monkeypatch
):
    from app.workers import editorial_render

    studio, calls, _ = reference_studio
    original = editorial_render.mockup
    fail_once = [True]

    def interrupted(data, artworks, geometry, **kwargs):
        if len(artworks) == 1 and fail_once[0]:
            fail_once[0] = False
            raise ValueError("Local composition interrupted")
        return original(data, artworks, geometry, **kwargs)

    monkeypatch.setattr(editorial_render, "mockup", interrupted)
    client, db, pid, _ = studio
    first = client.post(
        f"/v1/projects/{pid}/preview", headers={"Idempotency-Key": "interrupt-local"}
    )
    job = db.get(Job, uuid.UUID(first.json()["job_id"]))
    await runner.process_job(db, job)
    assert job.status == "DONE", job.error
    before = len(calls)
    assert before == 4
    recovered = await _run(studio, "preview", key="resume-local-no-new-image")
    assert recovered.status == "DONE", recovered.error
    assert len(calls) == before
    assert (
        client.get(f"/v1/projects/{pid}/assets").json()["in_hand_presentation"]
        == "book_only_fallback"
    )


@pytest.mark.asyncio
async def test_cover_calibration_waits_for_user_and_reuses_exact_cover(reference_studio):
    studio, calls, _ = reference_studio
    client, db, pid, store = studio
    job = await _run(studio, "preview", {"cover_only": True}, key="calibrate-cover")
    assert len(calls) == 1
    assert job.result["cover_only"] and job.result["preview_complete"] is False
    project = db.get(Project, uuid.UUID(pid))
    assert project.book_profile["stage"] == "cover_ready"
    proof = project.book_profile["cover_calibration"]
    original = store[proof["flat_key"]]
    assert not project.purchase_flow.get("preview_ready_at")
    assert client.post(f"/v1/projects/{pid}/preview/approve").status_code == 409
    assert client.get(f"/v1/projects/{pid}/preview/package").status_code == 409
    assert (
        client.post(
            f"/v1/projects/{pid}/preview", json={"approved_cover_sha256": "0" * 64}
        ).status_code
        == 409
    )
    assert len(calls) == 1
    await _run(studio, "preview", {"approved_cover_sha256": proof["sha256"]}, key="approve-cover")
    assert len(calls) == 4  # two pages and the optional holding scene; no second cover
    assert store[proof["flat_key"]] == original
    assert calls[1]["extra_refs"][-1] == store[proof["flat_meta"]["art_key"]]
    assert calls[2]["extra_refs"][-1] == store[proof["flat_meta"]["art_key"]]
    project = db.get(Project, uuid.UUID(pid))
    assert project.book_profile["stage"] == "preview_ready"
    assert not project.purchase_flow.get("preview_approved_at")
    assert client.get(f"/v1/projects/{pid}/preview/package").status_code == 200


@pytest.mark.asyncio
async def test_visual_master_is_not_attached_to_project_art(
    reference_studio, monkeypatch, tmp_path
):
    from cryptography.fernet import Fernet

    from app.services import visual_reference
    from app.workers import editorial_render

    key = Fernet.generate_key()
    cipher = Fernet(key)
    masters = {
        role: editorial_render.encode(Image.new("RGB", (32, 32), color))
        for role, color in (("cover", "green"), ("page", "blue"))
    }
    for role, data in masters.items():
        (tmp_path / f"visual-master-{role}.enc").write_bytes(cipher.encrypt(data))
    monkeypatch.setattr(visual_reference, "ROOT", tmp_path)
    monkeypatch.setattr(settings, "editorial_visual_reference_key", key.decode())
    studio, calls, _ = reference_studio
    await _run(studio, "preview", {"cover_only": True}, key="master-style-only")
    assert len(calls) == 1
    assert calls[0]["photo"] == _png()
    assert calls[0]["extra_refs"] == []
    assert "PROJECT-ONLY REFERENCES" in calls[0]["prompt"]
    _, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    from app.services import editorial_profile

    policy = editorial_profile.policy(project.book_profile)
    assert policy["typography"]["titleWidthRatio"] == 0.083
    assert policy["referenceComposition"]["coverRegion"][0] == 0.44
    assert visual_reference.load("cover", "cartoon") is None


@pytest.mark.asyncio
async def test_calibration_retry_does_not_generate_remaining_scenes(reference_studio):
    studio, calls, _ = reference_studio
    await _run(studio, "preview", {"cover_only": True}, key="first-cover")
    await _run(
        studio,
        "preview",
        {"image": "01_CAPA", "adjustment": "Mais parecido com a foto"},
        key="adjust-cover",
    )
    assert len(calls) == 2
    client, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    assert project.book_profile["stage"] == "cover_ready"
    assert len(client.get(f"/v1/projects/{pid}/assets").json()["previews"]) == 1


@pytest.mark.asyncio
async def test_changed_cover_cannot_continue_using_old_approval(reference_studio):
    studio, calls, _ = reference_studio
    client, db, pid, _ = studio
    await _run(studio, "preview", {"cover_only": True}, key="before-change")
    project = db.get(Project, uuid.UUID(pid))
    proof = project.book_profile["cover_calibration"]
    locale = {**project.book_profile["locales"]["pt-BR"], "title": "Outro título"}
    book_profile.update(project, locales={"pt-BR": locale})
    db.commit()
    response = client.post(
        f"/v1/projects/{pid}/preview", json={"approved_cover_sha256": proof["sha256"]}
    )
    assert response.status_code == 202
    job = db.get(Job, uuid.UUID(response.json()["job_id"]))
    await runner.process_job(db, job)
    db.refresh(job)
    assert job.status == "FAILED"
    assert "capa mudou" in job.error
    assert len(calls) == 1


def test_unreadable_visual_master_fails_before_generation(monkeypatch, tmp_path):
    from cryptography.fernet import Fernet

    from app.services import visual_reference

    monkeypatch.setattr(visual_reference, "ROOT", tmp_path)
    monkeypatch.setattr(settings, "editorial_visual_reference_key", Fernet.generate_key().decode())
    (tmp_path / "visual-master-cover.enc").write_bytes(b"invalid encrypted image")
    with pytest.raises(ProviderError, match="Referência visual indisponível"):
        visual_reference.load("cover", "realistic")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "style,title,family",
    [
        ("realistic", "João no parque", "adventure"),
        ("realistic", "Amor de Bisavó", "family"),
        ("cartoon", "Amor de Mãe", "cartoon"),
    ],
)
async def test_new_cover_uses_catalog_finish_and_keeps_project_photo(
    reference_studio, style, title, family
):
    from app.services import visual_reference

    studio, calls, _ = reference_studio
    _, db, pid, _ = studio
    project = db.get(Project, uuid.UUID(pid))
    project.style = style
    project.theme = title
    locale = {**project.book_profile["locales"]["pt-BR"], "title": title}
    book_profile.update(project, locales={"pt-BR": locale})
    db.commit()
    await _run(studio, "preview", {"cover_only": True}, key="catalog-first-cover")
    assert len(calls) == 1
    assert calls[0]["photo"] == _png()
    assert calls[0]["extra_refs"] == []
    assert "PROJECT-ONLY REFERENCES" in calls[0]["prompt"]
    assert visual_reference.catalog_family(style, title) == family
