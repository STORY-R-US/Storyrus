"""Review evidence is validated independently of model prose and never implies approval."""

import json
import re
import unicodedata

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


# --- Falsos positivos da revisão automática ------------------------------------
# O revisor às vezes reprova citando o MESMO texto como "esperado" e "observado"
# (só muda quebra de linha, espaço ou acento), declara "no error" no próprio item,
# ou lista incerteza probabilística como defeito. Esses itens não descrevem um
# defeito visível; ficam registrados em `limitations`/`discarded_issues`.
_QUOTED = re.compile(r"'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\"|“([^”]*)”")
_SELF_CLEARED = (
    "no error",
    "not an error",
    "no issue",
    "not a defect",
    "does not constitute a defect",
    "provided for clarity",
    "only line wrapping differs",
    "wrapping or justification alone",
    "sem erro",
    "não é erro",
    "não é um erro",
    "não constitui defeito",
)
_UNCERTAINTY_ONLY = (
    "probabilistic",
    "probabilístic",
    "probabilistic limits",
    "uncertainty implies",
    "must be reported as a limitation",
    "must be disclosed as a limitation",
    "remains borderline",
    "borders on being",
    "biometric certainty",
    "certeza biométrica",
    "confirmação probabilística",
)


def _normalized_text(value: str) -> str:
    value = value.replace("\\n", " ").replace("\\t", " ")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return " ".join(value.casefold().split())


def _identical_quotes(issue: str) -> bool:
    quotes = [
        next(group for group in match.groups() if group is not None)
        for match in _QUOTED.finditer(issue)
    ]
    quotes = [quote for quote in quotes if len(quote.strip()) >= 8]
    if len(quotes) < 2 or len(quotes) % 2:
        return False
    normalized = [_normalized_text(quote) for quote in quotes]
    return all(normalized[i] == normalized[i + 1] for i in range(0, len(normalized), 2))


def false_positive(issue: str) -> bool:
    """Item que o próprio revisor descreve como inexistente ou só incerto."""
    low = issue.casefold()
    if any(marker in low for marker in _SELF_CLEARED):
        return True
    if "TEXT_INVALID" in issue.upper() and _identical_quotes(issue):
        return True
    return any(marker in low for marker in _UNCERTAINTY_ONLY)


def without_false_positives(report):
    """Remove itens sem defeito visível; aprova só se não restar nenhum item."""
    issues = list(report.get("issues") or [])
    codes = report.get("issue_codes")
    kept, kept_codes, discarded = [], [], []
    for index, issue in enumerate(issues):
        if false_positive(issue):
            discarded.append(issue)
            continue
        kept.append(issue)
        if isinstance(codes, list):
            kept_codes.append(codes[index])
    if not discarded:
        return report
    cleaned = {
        **report,
        "issues": kept,
        "limitations": [*report.get("limitations", []), *discarded][:64],
        "discarded_issues": discarded,
    }
    if isinstance(codes, list):
        cleaned["issue_codes"] = kept_codes
    if not kept and report.get("valid") is False and issues:
        # Todos os motivos citados eram falsos positivos: nada concreto a corrigir.
        cleaned["valid"] = True
    return cleaned
