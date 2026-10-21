"""Guardrails de custo da plataforma (STO-18).

Antes de enfileirar ou chamar vendor: checa teto diario opcional de USD e de
creditos debitados. 0 / None nos settings = desligado.

O painel /gastos consome `anomalies()` para alertar burn anômalo.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, load_only

from app.config import settings
from app.models import Job, JobStatus
from app.services.pricing import _f, estimate_job_usd

logger = logging.getLogger(__name__)

_TZ = ZoneInfo("America/Sao_Paulo")


class SpendCeilingError(Exception):
    """Teto diario de USD ou creditos atingido — nao chamar vendor."""

    def __init__(self, message: str, *, kind: str = "usd"):
        self.kind = kind
        super().__init__(message)


@dataclass(frozen=True)
class DaySpend:
    timezone: str
    from_at: datetime
    to_at: datetime
    measured_usd: float
    reserved_usd: float
    committed_usd: float
    credits_spent: int


@dataclass(frozen=True)
class Anomaly:
    kind: str
    severity: str  # info | warn | critical
    message: str


def today_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    local = (now or datetime.now(UTC)).astimezone(_TZ)
    start = datetime.combine(local.date(), time.min, tzinfo=_TZ).astimezone(UTC)
    end = datetime.combine(local.date(), time.max, tzinfo=_TZ).astimezone(UTC)
    return start, end


def _empty_spend(now: datetime | None = None) -> DaySpend:
    start, end = today_window(now)
    return DaySpend(
        timezone="America/Sao_Paulo",
        from_at=start,
        to_at=end,
        measured_usd=0.0,
        reserved_usd=0.0,
        committed_usd=0.0,
        credits_spent=0,
    )


def _aware(dt: object) -> datetime | None:
    """Normaliza created_at. Linha corrompida não pode derrubar o enqueue."""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(dt, datetime):
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def day_spend(db: Session, *, now: datetime | None = None) -> DaySpend:
    """USD medido + reservado (PENDING/RUNNING sem cost_usd) e creditos do dia."""
    start, end = today_window(now)
    # Só as colunas do teto — `result` pode ser JSON grande e estourar a instância.
    rows = db.scalars(
        select(Job)
        .options(
            load_only(
                Job.id,
                Job.created_at,
                Job.status,
                Job.cost_usd,
                Job.cost_credits,
                Job.type,
            )
        )
        .order_by(Job.created_at.desc())
        .limit(2000)
    ).all()

    measured = 0.0
    reserved = 0.0
    credits = 0
    for job in rows:
        try:
            created = _aware(job.created_at)
            if created is None or not (start <= created <= end):
                continue
            usd = _f(job.cost_usd) if job.cost_usd is not None else None
            if usd is not None:
                measured += usd
            elif job.status in (JobStatus.PENDING.value, JobStatus.RUNNING.value):
                reserved += estimate_job_usd(job.type)
            # Creditos ainda "queimados" (FAILED ja estornou).
            if job.status != JobStatus.FAILED.value and job.cost_credits:
                credits += int(job.cost_credits or 0)
        except Exception:  # noqa: BLE001 - uma linha ruim não derruba o teto
            logger.warning("day_spend ignorou job %s", getattr(job, "id", "?"))
            continue

    measured = round(measured, 6)
    reserved = round(reserved, 6)
    return DaySpend(
        timezone="America/Sao_Paulo",
        from_at=start,
        to_at=end,
        measured_usd=measured,
        reserved_usd=reserved,
        committed_usd=round(measured + reserved, 6),
        credits_spent=credits,
    )


def _guarded_spend(db: Session) -> DaySpend:
    """Leitura do teto. Falha de scan não pode virar HTTP 500 na prévia."""
    try:
        return day_spend(db)
    except Exception:  # noqa: BLE001 - scan do teto não pode virar HTTP 500
        logger.exception("day_spend falhou; teto ignorado nesta tentativa")
        return _empty_spend()


def assert_can_enqueue(db: Session, job_type: str, *, cost_credits: int = 0) -> DaySpend:
    """Falha se o novo job estouraria o teto diario (USD ou creditos)."""
    usd_ceiling = float(settings.daily_spend_usd_ceiling or 0.0)
    credits_ceiling = int(settings.daily_credits_ceiling or 0)
    # Produção deixa os tetos em 0. Não varrer a tabela de jobs à toa:
    # um result JSON grande ou uma linha ruim derrubava POST /preview com 500.
    if usd_ceiling <= 0 and (credits_ceiling <= 0 or cost_credits <= 0):
        return _empty_spend()

    spend = _guarded_spend(db)
    est = estimate_job_usd(job_type)

    if usd_ceiling > 0 and spend.committed_usd + est > usd_ceiling + 1e-9:
        raise SpendCeilingError(
            f"Teto diario de USD atingido: "
            f"comprometido {spend.committed_usd:.4f} + estimado {est:.4f} "
            f"> teto {usd_ceiling:.4f}",
            kind="usd",
        )

    if credits_ceiling > 0 and cost_credits > 0:
        if spend.credits_spent + cost_credits > credits_ceiling:
            raise SpendCeilingError(
                f"Teto diario de creditos atingido: "
                f"hoje {spend.credits_spent} + {cost_credits} "
                f"> teto {credits_ceiling}",
                kind="credits",
            )
    return spend


def assert_vendor_allowed(db: Session, job_type: str | None = None) -> DaySpend:
    """Antes do vendor: se o teto USD ja foi medido, nao gasta mais.

    Jobs PENDING/RUNNING ja contam no reserved em assert_can_enqueue; aqui
    bloqueamos quando o burn real (medido) ja bateu o teto.
    """
    usd_ceiling = float(settings.daily_spend_usd_ceiling or 0.0)
    credits_ceiling = int(settings.daily_credits_ceiling or 0)
    if usd_ceiling <= 0 and credits_ceiling <= 0:
        return _empty_spend()

    spend = _guarded_spend(db)
    if usd_ceiling > 0 and spend.measured_usd >= usd_ceiling - 1e-9:
        raise SpendCeilingError(
            f"Teto diario de USD atingido ({spend.measured_usd:.4f} >= {usd_ceiling:.4f}); "
            f"recusando chamada de vendor" + (f" para {job_type}" if job_type else ""),
            kind="usd",
        )

    if credits_ceiling > 0 and spend.credits_spent >= credits_ceiling:
        raise SpendCeilingError(
            f"Teto diario de creditos atingido "
            f"({spend.credits_spent} >= {credits_ceiling}); "
            f"recusando chamada de vendor",
            kind="credits",
        )
    return spend


def anomalies(db: Session, *, today_usd: float | None = None) -> list[Anomaly]:
    """Sinais leves para o painel /gastos (sem mudar a landing)."""
    spend = day_spend(db)
    measured = today_usd if today_usd is not None else spend.measured_usd
    out: list[Anomaly] = []

    usd_ceiling = float(settings.daily_spend_usd_ceiling or 0.0)
    if usd_ceiling > 0:
        ratio = measured / usd_ceiling if usd_ceiling else 0.0
        warn_at = float(settings.spend_anomaly_warn_ratio or 0.8)
        if measured >= usd_ceiling - 1e-9:
            out.append(
                Anomaly(
                    kind="daily_usd_ceiling",
                    severity="critical",
                    message=(f"Teto diario de USD atingido: {measured:.4f} / {usd_ceiling:.4f}"),
                )
            )
        elif ratio >= warn_at:
            out.append(
                Anomaly(
                    kind="daily_usd_warn",
                    severity="warn",
                    message=(
                        f"Burn do dia em {ratio:.0%} do teto ({measured:.4f} / {usd_ceiling:.4f})"
                    ),
                )
            )
        if spend.reserved_usd > 0 and spend.committed_usd >= usd_ceiling - 1e-9:
            out.append(
                Anomaly(
                    kind="daily_usd_reserved",
                    severity="warn",
                    message=(
                        f"USD comprometido (medido+fila) {spend.committed_usd:.4f} "
                        f">= teto {usd_ceiling:.4f} "
                        f"(reservado na fila: {spend.reserved_usd:.4f})"
                    ),
                )
            )

    credits_ceiling = int(settings.daily_credits_ceiling or 0)
    if credits_ceiling > 0 and spend.credits_spent >= credits_ceiling:
        out.append(
            Anomaly(
                kind="daily_credits_ceiling",
                severity="critical",
                message=(
                    f"Teto diario de creditos atingido: {spend.credits_spent} / {credits_ceiling}"
                ),
            )
        )

    abs_warn = float(settings.spend_anomaly_usd or 0.0)
    if abs_warn > 0 and measured >= abs_warn - 1e-9:
        out.append(
            Anomaly(
                kind="abs_usd_burn",
                severity="warn",
                message=f"Burn do dia {measured:.4f} USD acima do alarme {abs_warn:.4f}",
            )
        )

    return out
