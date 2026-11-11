"""Exercise restart/new-job boundaries without contacting a provider."""

import asyncio
import json
import uuid

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.ai_clients.base import ImageResult, ProviderError, TextResult
from app.ai_clients.request_journal import client_request_id, journaled, request_journal
from app.database import Base
from app.models import Asset, Job, Project, User
from app.schemas import JobOut


@pytest.fixture
def setup(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        user = User(email="journal@test.com", password_hash="x")
        db.add(user)
        db.flush()
        project = Project(user_id=user.id, style="cartoon")
        db.add(project)
        db.flush()
        job = Job(project_id=project.id, type="EBOOK", status="RUNNING")
        db.add(job)
        db.commit()
        objects = {}
        monkeypatch.setattr(
            "app.storage.put_bytes", lambda key, data, *_: objects.update({key: data})
        )
        monkeypatch.setattr("app.storage.get_bytes", lambda key: objects[key])
        yield db, job, objects


class Provider:
    def __init__(self, db, job, *, failure=None, image=False):
        self.db, self.job = db, job
        self.failure, self.image = failure, image
        self.calls = 0

    @journaled("test:paid")
    async def generate(self, *, prompt, photo=b"private-photo"):
        self.calls += 1
        request_id = client_request_id()
        # Observe the committed reservation from a different connection/session.
        self.db.expire_all()
        saved = list(self.job.result["paid_requests"].values())[-1]
        assert saved["state"] == "started"
        assert saved["client_request_id"] == request_id
        if self.failure:
            if isinstance(self.failure, ProviderError):
                self.failure.client_request_id = request_id
            raise self.failure
        meta = {"request_id": "req-server", "client_request_id": request_id}
        if self.image:
            return ImageResult(b"image-bytes", cost_usd=0.04, meta=meta)
        return TextResult("private-result", cost_usd=0.01, meta=meta)


@pytest.mark.asyncio
@pytest.mark.parametrize("image", [False, True])
async def test_completed_output_survives_worker_restart_without_another_charge(setup, image):
    db, job, _ = setup
    provider = Provider(db, job, image=image)
    with request_journal(db, job):
        first = await provider.generate(prompt="private-prompt")
    with request_journal(db, job):
        recovered = await provider.generate(prompt="private-prompt")
    assert provider.calls == 1
    assert recovered.cost_usd == 0
    assert recovered.meta["reused"] is True
    assert recovered.meta["request_id"] == first.meta["request_id"]
    assert db.scalar(select(Asset)).kind == "provider_result"
    if image:
        assert recovered.image_bytes == first.image_bytes
    else:
        assert recovered.text == first.text
    metadata = json.dumps(job.result)
    assert "private-prompt" not in metadata
    assert "private-photo" not in metadata
    assert "private-result" not in metadata
    assert "paid_requests" not in JobOut.model_validate(job).model_dump()["result"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure",
    [
        ProviderError("timeout", transient=True, outcome_unknown=True),
        asyncio.CancelledError(),
    ],
)
async def test_uncertain_or_interrupted_request_is_blocked_even_in_new_job(setup, failure):
    db, job, _ = setup
    provider = Provider(db, job, failure=failure)
    with request_journal(db, job):
        with pytest.raises(type(failure)):
            await provider.generate(prompt="same")
    for new_job in [job, Job(project_id=job.project_id, type="EBOOK", status="RUNNING")]:
        db.add(new_job)
        db.commit()
        with request_journal(db, new_job):
            with pytest.raises(ProviderError, match="GENERATION_OUTCOME_UNKNOWN") as caught:
                await provider.generate(prompt="same")
        assert caught.value.retry_safe is False
        assert caught.value.client_request_id
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_explicit_rate_limit_can_be_retried_but_missing_cached_output_cannot(setup):
    db, job, objects = setup
    provider = Provider(db, job, failure=ProviderError("429", transient=True, status_code=429))
    with request_journal(db, job):
        with pytest.raises(ProviderError):
            await provider.generate(prompt="same")
    provider.failure = None
    with request_journal(db, job):
        await provider.generate(prompt="same")
    assert provider.calls == 2
    objects.clear()
    with request_journal(db, job):
        with pytest.raises(ProviderError, match="GENERATION_OUTCOME_UNKNOWN"):
            await provider.generate(prompt="same")
    assert provider.calls == 2
    other = Job(project_id=job.project_id, type="EBOOK", status="RUNNING")
    db.add(other)
    db.commit()
    with request_journal(db, other):
        with pytest.raises(ProviderError, match="GENERATION_OUTCOME_UNKNOWN"):
            await provider.generate(prompt="same")
    assert provider.calls == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("edit", [False, True])
@pytest.mark.parametrize("failure", ["timeout", 408, 503])
async def test_openai_transport_is_journaled_before_send_and_never_repeated(
    setup, monkeypatch, edit, failure
):
    from app.ai_clients import image_openai

    db, job, _ = setup
    calls = []

    class Transport:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            pass

        async def post(self, url, **kwargs):
            calls.append(kwargs)
            saved = next(iter(job.result["paid_requests"].values()))
            assert saved["state"] == "started"
            assert saved["client_request_id"] == kwargs["headers"]["X-Client-Request-Id"]
            if failure == "timeout":
                raise httpx.ReadTimeout("response lost")
            return httpx.Response(
                failure,
                headers={"x-request-id": "req-test"},
                json={"error": {"code": "server_error"}},
            )

    monkeypatch.setattr(image_openai.httpx, "AsyncClient", Transport)
    provider = image_openai.OpenAIImageProvider(api_key="test-key")

    async def generate():
        return await provider.generate_character(
            prompt="same", reference_images=[b"photo"] if edit else [], style="cartoon"
        )

    with request_journal(db, job):
        with pytest.raises(ProviderError) as caught:
            await generate()
    assert caught.value.outcome_unknown is True
    with request_journal(db, job):
        with pytest.raises(ProviderError, match="GENERATION_OUTCOME_UNKNOWN"):
            await generate()
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_uncertain_request_does_not_block_different_input_or_other_project(setup):
    db, job, _ = setup
    provider = Provider(db, job, failure=ProviderError("timeout", outcome_unknown=True))
    with request_journal(db, job):
        with pytest.raises(ProviderError):
            await provider.generate(prompt="one")
    provider.failure = None
    with request_journal(db, job):
        await provider.generate(prompt="two")
    project = Project(
        id=uuid.uuid4(), user_id=db.get(Project, job.project_id).user_id, style="cartoon"
    )
    db.add(project)
    db.flush()
    other = Job(project_id=project.id, type="EBOOK", status="RUNNING")
    db.add(other)
    db.commit()
    provider.job = other
    with request_journal(db, other):
        await provider.generate(prompt="one")
    assert provider.calls == 3
