"""Itens da revisão automática que não descrevem defeito visível não bloqueiam a prévia."""

from app.services import editorial_review

# Itens reais registrados em produção em 13 e 16/11/2026.
LINE_BREAK_ONLY = (
    "TEXT_INVALID: expected 'Andre decide criar algo novo,\\nja abre o programa com um "
    "clique leve.' and found 'Andre decide criar algo novo, já abre o programa com um "
    "clique leve.'."
)
LEADING_SPACES = (
    "TEXT_INVALID: Expected 'Testa as cores, mistura tons no visor,\\nsurge um sorriso' "
    "but observed 'Testa as cores, mistura tons no visor,\\n surge um sorriso' "
    "(there are additional leading spaces on lines 2-4)"
)
SELF_CLEARED = (
    "TEXT_INVALID: expected 'Testa as cores' and found 'Testa as cores' "
    "(no error here, provided for clarity)."
)
UNCERTAIN_IDENTITY = (
    "IDENTITY: There is a reasonable likeness, but as probabilistic limits exist and "
    "identity confirmation is required, uncertainty implies invalid."
)
REAL_TEXT = "TEXT_INVALID: expected 'Andre decide criar algo novo' but observed 'Andre decidiu'"
REAL_ANATOMY = "ANATOMY: O braço esquerdo apresenta uma transição desconexa com o antebraço."


def test_false_positives_alone_approve_the_review():
    report = {
        "valid": False,
        "issues": [LINE_BREAK_ONLY, LEADING_SPACES, SELF_CLEARED, UNCERTAIN_IDENTITY],
        "limitations": ["general"],
    }
    cleaned = editorial_review.without_false_positives(report)
    assert editorial_review.approved(cleaned)
    assert cleaned["discarded_issues"] == report["issues"]
    assert set(report["issues"]) <= set(cleaned["limitations"])


def test_concrete_defects_remain_blocking_and_codes_stay_aligned():
    report = {
        "valid": False,
        "issues": [LINE_BREAK_ONLY, REAL_TEXT, REAL_ANATOMY],
        "issue_codes": ["TEXT_INVALID", "TEXT_INVALID", "ANATOMY"],
        "limitations": [],
    }
    cleaned = editorial_review.without_false_positives(report)
    assert not editorial_review.approved(cleaned)
    assert cleaned["issues"] == [REAL_TEXT, REAL_ANATOMY]
    assert cleaned["issue_codes"] == ["TEXT_INVALID", "ANATOMY"]


def test_clean_or_empty_inconclusive_reports_are_unchanged():
    approved = {"valid": True, "issues": [], "limitations": []}
    assert editorial_review.without_false_positives(approved) is approved
    inconclusive = {"valid": False, "issues": [], "limitations": ["unreadable"]}
    cleaned = editorial_review.without_false_positives(inconclusive)
    assert not editorial_review.approved(cleaned)
