"""Review evidence is validated independently of model prose and never implies approval."""

import json

from app.ai_clients.base import ProviderError

ISSUE_CODES = {
    "TEXT_OVERLAP",
    "TEXT_CONTRAST",
    "TEXT_INVALID",
    "IDENTITY",
    "ANATOMY",
    "STYLE",
    "SCENE",
    "COLLAGE",
    "GEOMETRY",
    "INCONCLUSIVE",
}


def parse_report(text):
    try:
        report = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise ProviderError("BOOK_REVIEW_INVALID: resposta de revisão inválida") from exc
    if (
        not isinstance(report, dict)
        or type(report.get("valid")) is not bool
        or any(
            not isinstance(report.get(key), list)
            or len(report[key]) > 64
            or any(not isinstance(item, str) or not item.strip() for item in report[key])
            for key in ("issues", "limitations")
        )
    ):
        raise ProviderError("BOOK_REVIEW_INVALID: contrato de revisão inválido")
    codes = report.get("issue_codes")
    if codes is not None and (
        not isinstance(codes, list)
        or len(codes) != len(report["issues"])
        or any(not isinstance(code, str) or code not in ISSUE_CODES for code in codes)
    ):
        raise ProviderError("BOOK_REVIEW_INVALID: classificação de revisão inválida")
    return report


def approved(report):
    return report["valid"] is True and report["issues"] == []


def overlap_only(report):
    return bool(
        report["issues"] and report.get("issue_codes") == ["TEXT_OVERLAP"] * len(report["issues"])
    )
