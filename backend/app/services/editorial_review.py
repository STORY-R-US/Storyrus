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


def parse_crop_report(text, expected_lines):
    """Accept complete per-line evidence without discarding any rejection."""
    try:
        value = json.loads(text)
    except (ValueError, TypeError):
        return parse_report(text)
    if isinstance(value, dict) and set(value) == {
        f"line {number}" for number in range(1, expected_lines + 1)
    }:
        if any(not isinstance(row, dict) or "line" in row for row in value.values()):
            raise ProviderError("BOOK_REVIEW_INVALID: revisão por linha inválida")
        value = {
            "results": [
                {**value[f"line {number}"], "line": number}
                for number in range(1, expected_lines + 1)
            ]
        }
    elif isinstance(value, dict) and any(key.startswith("line ") for key in value):
        raise ProviderError("BOOK_REVIEW_INVALID: revisão por linha incompleta ou conflitante")
    if not isinstance(value, dict) or "results" not in value:
        return parse_report(text)
    rows = value["results"]
    if (
        set(value) != {"results"}
        or not isinstance(rows, list)
        or len(rows) != expected_lines
        or any(not isinstance(row, dict) or type(row.get("line")) is not int for row in rows)
        or sorted(row["line"] for row in rows) != list(range(1, expected_lines + 1))
    ):
        raise ProviderError("BOOK_REVIEW_INVALID: revisão por linha incompleta")
    reports = [parse_report(json.dumps(row)) for row in rows]
    return {
        "valid": all(approved(report) for report in reports),
        "issues": [
            f"Line {row['line']}: {issue}"
            for row, report in zip(rows, reports, strict=True)
            for issue in report["issues"]
        ],
        "limitations": list(
            dict.fromkeys(note for report in reports for note in report["limitations"])
        ),
    }


def overlap_only(report):
    return bool(
        report["issues"] and report.get("issue_codes") == ["TEXT_OVERLAP"] * len(report["issues"])
    )
