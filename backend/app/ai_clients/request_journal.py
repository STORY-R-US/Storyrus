"""Durable, project-scoped protection around paid OpenAI calls.

Request IDs are for tracing, not provider-side idempotency. An interrupted
request is never sent again automatically. Received outputs are private assets,
so a worker restart can reuse them without buying the same result again.
"""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict
from datetime import UTC, datetime
from functools import wraps

from sqlalchemy import select

from app import storage
from app.ai_clients.base import ImageResult, ProviderError, TextResult
from app.models import Asset, Job, Project

_current: ContextVar = ContextVar("paid_request_journal", default=None)
_request_id: ContextVar = ContextVar("paid_client_request_id", default=None)


def client_request_id() -> str:
    reserve = _request_id.get()
    return reserve() if reserve else str(uuid.uuid4())


def _hashable(value):
    if isinstance(value, bytes):
        return {"sha256": hashlib.sha256(value).hexdigest()}
    if isinstance(value, dict):
        return {key: _hashable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_hashable(item) for item in value]
    return value


def _unknown(entry):
    return ProviderError(
        "GENERATION_OUTCOME_UNKNOWN",
        retry_safe=False,
        outcome_unknown=True,
        request_id=entry.get("request_id"),
        client_request_id=entry.get("client_request_id"),
        status_code=entry.get("status_code"),
    )


def unresolved_request(job):
    entries = (job.result or {}).get("paid_requests") or {}
    return next(
        (
            entry
            for entry in reversed(list(entries.values()))
            if entry.get("state") in {"started", "unknown"}
        ),
        None,
    )


class RequestJournal:
    def __init__(self, db, job):
        self.db, self.job = db, job

    def _save(self, key, entry):
        entries = dict((self.job.result or {}).get("paid_requests") or {})
        entries[key] = entry
        self.job.result = {**(self.job.result or {}), "paid_requests": entries}
        self.db.commit()

    def begin(self, operation, fingerprint):
        key = fingerprint
        # The project row serializes reservations made by separate workers/jobs.
        self.db.flush()
        self.db.execute(
            select(Project.id).where(Project.id == self.job.project_id).with_for_update()
        ).first()
        rows = self.db.execute(
            select(Job.id, Job.result)
            .where(Job.project_id == self.job.project_id)
            .order_by(Job.created_at.desc(), Job.id.desc())
        ).all()
        completed = None
        payload = (self.job.result or {}).get("payload") or {}
        explicit_new_image = (
            operation.startswith("openai:image")
            and payload.get("image")
            and not payload.get("title_refresh")
        )
        for job_id, result in rows:
            for entry in ((result or {}).get("paid_requests") or {}).values():
                if entry.get("fingerprint") != fingerprint:
                    continue
                if entry.get("state") in {"started", "unknown"}:
                    self.db.commit()
                    raise _unknown(entry)
                if (
                    completed is None
                    and entry.get("state") == "done"
                    and (job_id == self.job.id or not explicit_new_image)
                ):
                    completed = entry
        if completed:
            self.db.commit()
            try:
                raw = storage.get_bytes(completed["storage_key"])
                if hashlib.sha256(raw).hexdigest() != completed["sha256"]:
                    raise ValueError("provider cache checksum mismatch")
                body = json.loads(raw)
                meta = {**body["meta"], "reused": True}
                if body["kind"] == "image":
                    output = ImageResult(
                        base64.b64decode(body["image_bytes"], validate=True),
                        mime_type=body["mime_type"],
                        cost_usd=0,
                        meta=meta,
                    )
                elif body["kind"] == "text":
                    output = TextResult(body["text"], cost_usd=0, meta=meta)
                else:
                    raise ValueError("unknown provider cache kind")
                # A new retry job must inherit the receipt as well as the output.
                # Otherwise a crash between provider completion and stage storage
                # can buy the exact same result again in the next job.
                self._save(key, completed)
                return key, completed, output
            except Exception as exc:
                if storage.is_transient_error(exc):
                    # The paid result is known and durably saved. Retry its READ,
                    # never turn a temporary object-store outage into uncertainty.
                    raise ProviderError(
                        "BOOK_STORAGE_TEMPORARY",
                        transient=True,
                        retry_safe=True,
                        request_id=completed.get("request_id"),
                    ) from exc
                # An unavailable cache is not permission to purchase another output.
                self._save(key, {**completed, "state": "unknown"})
                raise _unknown(completed) from exc
        entry = {
            "fingerprint": fingerprint,
            "operation": operation,
            "state": "started",
            "client_request_id": str(uuid.uuid4()),
            "started_at": datetime.now(UTC).isoformat(),
        }
        self._save(key, entry)
        return key, entry, None

    def finish(self, key, entry, output):
        body = asdict(output)
        if isinstance(output, ImageResult):
            body["image_bytes"] = base64.b64encode(output.image_bytes).decode("ascii")
            body["kind"] = "image"
        else:
            body["kind"] = "text"
        asset_key = storage.new_key(self.job.project_id, "provider_result", "json")
        raw = json.dumps(body).encode("utf-8")
        storage.put_bytes(asset_key, raw, "application/json")
        self.db.add(
            Asset(
                project_id=self.job.project_id,
                kind="provider_result",
                storage_key=asset_key,
                meta={"fingerprint": entry["fingerprint"]},
            )
        )
        self._save(
            key,
            {
                **entry,
                "state": "done",
                "storage_key": asset_key,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "request_id": output.meta.get("request_id"),
            },
        )

    def fail(self, key, entry, exc):
        self._save(
            key,
            {
                **entry,
                "state": "unknown" if exc.outcome_unknown else "failed",
                "request_id": exc.request_id,
                "client_request_id": exc.client_request_id or entry["client_request_id"],
                "status_code": exc.status_code,
            },
        )


@contextmanager
def request_journal(db, job):
    token = _current.set(RequestJournal(db, job))
    try:
        yield
    finally:
        _current.reset(token)


def journaled(operation):
    def decorate(call):
        @wraps(call)
        async def wrapped(self, *args, **kwargs):
            journal = _current.get()
            if journal is None:
                return await call(self, *args, **kwargs)
            fingerprint = hashlib.sha256(
                json.dumps(
                    _hashable([operation, getattr(self, "_model", None), args, kwargs]),
                    sort_keys=True,
                    ensure_ascii=True,
                ).encode("utf-8")
            ).hexdigest()
            key, entry, cached = journal.begin(operation, fingerprint)
            if cached is not None:
                if hasattr(self, "last_cost_usd"):
                    self.last_cost_usd = 0
                return cached

            def reserve_request_id():
                entry["client_request_id"] = str(uuid.uuid4())
                journal._save(key, entry)
                return entry["client_request_id"]

            token = _request_id.set(reserve_request_id)
            try:
                output = await call(self, *args, **kwargs)
                journal.finish(key, entry, output)
                return output
            except ProviderError as exc:
                journal.fail(key, entry, exc)
                raise
            finally:
                # Unexpected failures/cancellation leave the committed started marker.
                _request_id.reset(token)

        return wrapped

    return decorate
