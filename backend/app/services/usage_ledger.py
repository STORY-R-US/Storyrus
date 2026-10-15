"""Ledger de cada chamada de IA (uma linha no extrato)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import Job, UsageEvent
from app.services.pricing import _f


def usage_line(
    *,
    action: str,
    label: str,
    cost_usd: float | None,
    provider: str = "openai",
    kind: str = "image",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "provider": provider,
        "action": action,
        "label": label,
        "cost_usd": None if cost_usd is None else round(_f(cost_usd), 6),
        "meta": meta or {},
    }


def append_usage(result: Any, line: dict[str, Any]) -> None:
    """Anexa uma linha em `result.meta['usage_lines']` sem alterar cost_usd."""
    meta = dict(getattr(result, "meta", None) or {})
    lines = list(meta.get("usage_lines") or [])
    lines.append(line)
    meta["usage_lines"] = lines
    result.meta = meta


def merge_usage(old: Any, new: Any) -> None:
    """Copia linhas do resultado anterior para o novo (refine substitui o objeto)."""
    old_lines = list((getattr(old, "meta", None) or {}).get("usage_lines") or [])
    new_meta = dict(getattr(new, "meta", None) or {})
    new_lines = list(new_meta.get("usage_lines") or [])
    new_meta["usage_lines"] = old_lines + new_lines
    new.meta = new_meta


def lines_of(result: Any) -> list[dict[str, Any]]:
    return list((getattr(result, "meta", None) or {}).get("usage_lines") or [])


def image_provider_name(result: Any, fallback: str | None = None) -> str:
    meta = getattr(result, "meta", None) or {}
    raw = meta.get("provider") or meta.get("head_provider") or fallback or "openai"
    # Aliases legados (rows antigas no extrato).
    if raw in ("nano-banana", "gemini"):
        return "gemini"
    if raw in ("openai", "gpt-image-1"):
        return "openai"
    if raw in ("pulid", "pulid-fal", "fal"):
        return "fal"
    return str(raw)


def record_usage(
    db: Session,
    *,
    job: Job,
    kind: str,
    provider: str,
    action: str,
    label: str,
    cost_usd: float | None,
    meta: dict[str, Any] | None = None,
) -> UsageEvent:
    event = UsageEvent(
        job_id=job.id,
        project_id=job.project_id,
        kind=kind,
        provider=provider,
        action=action,
        label=label,
        cost_usd=None if cost_usd is None else round(_f(cost_usd), 6),
        meta=meta or {},
    )
    db.add(event)
    return event


def flush_usage(db: Session, job: Job, lines: list[dict[str, Any]] | None) -> None:
    for line in lines or []:
        record_usage(
            db,
            job=job,
            kind=str(line.get("kind") or "image"),
            provider=str(line.get("provider") or "openai"),
            action=str(line.get("action") or "generate"),
            label=str(line.get("label") or "Geração"),
            cost_usd=line.get("cost_usd"),
            meta=line.get("meta") if isinstance(line.get("meta"), dict) else {},
        )


def unmeasured_job_line(job: Job) -> dict[str, Any]:
    return usage_line(
        action="job_total",
        label="Job sem extrato (antes do ledger)",
        cost_usd=float(job.cost_usd) if job.cost_usd is not None else None,
        provider=job.provider or "desconhecido",
        kind="job",
        meta={"job_id": str(job.id), "job_type": job.type},
    )
