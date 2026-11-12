"""Lossless recovery of provider formatting; never invent missing content."""

import json
import re


def object_from_text(text):
    if not isinstance(text, str):
        raise ValueError("Expected provider text")
    value = text.strip().lstrip("\ufeff").strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", value, flags=re.I | re.S)
    if fence:
        value = fence.group(1)
    value = json.loads(value)
    # Some providers return a JSON string containing the requested object.
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, dict):
        raise ValueError("Expected one complete object")
    return value


def normalize_locales(prepared, languages):
    result = dict(prepared)
    locales = result.get("locales")
    if not isinstance(locales, dict):
        raise ValueError("Missing localized content")
    normalized = dict(locales)
    for language in languages:
        if language not in normalized:
            matches = [
                key
                for key in locales
                if str(key).lower().replace("_", "-")
                in {language.lower(), "pt" if language == "pt-BR" else language.lower()}
            ]
            if len(matches) != 1:
                raise ValueError("Missing or ambiguous locale")
            normalized[language] = locales[matches[0]]
        locale = normalized[language]
        if not isinstance(locale, dict):
            raise ValueError("Invalid locale")
        locale = dict(locale)
        for key in ("left", "right"):
            lines = locale.get(key)
            if isinstance(lines, list) and lines and all(isinstance(line, str) for line in lines):
                locale[key] = "\n".join(lines)
        normalized[language] = locale
    result["locales"] = {language: normalized[language] for language in languages}
    return result
