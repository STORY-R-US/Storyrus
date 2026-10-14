"""Resumo do pedido que o dono lê quando a família cria o livro e envia a foto."""

from __future__ import annotations

import re

_SPLIT = re.compile(r"[,;\n]+")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def language_label(code: str | None) -> str:
    """Rótulo em português para o idioma já escolhido no site (pt / en / es)."""
    key = (code or "pt").strip().lower().replace("_", "-")
    if key.startswith("en"):
        return "Inglês"
    if key.startswith("es"):
        return "Espanhol"
    return "Português"


def parse_extra_names(raw: str | None) -> list[str]:
    if not raw:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for part in _SPLIT.split(raw):
        name = " ".join(part.split())
        if not name:
            continue
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(name)
    return out


_SUBJECT = {
    "crianca": "Criança",
    "pet": "Pet",
    "pai": "Pai",
    "mae": "Mãe",
    "tia": "Tia",
    "bisavo": "Bisavó",
    "primo": "Primo",
    "avo": "Avó",
    "avoh": "Avô",
}

_ALSO_NAME = {
    "crianca": "Nome da criança",
    "pet": "Nome do pet",
    "pai": "Nome do pai",
    "mae": "Nome da mãe",
    "tia": "Nome da tia",
    "bisavo": "Nome da bisavó",
    "primo": "Nome do primo",
    "avo": "Nome da avó",
    "avoh": "Nome do avô",
}

_ALSO_GENDER = {
    "crianca": "Gênero da criança",
    "pet": "Gênero do pet",
    "pai": "Gênero do pai",
    "mae": "Gênero da mãe",
    "tia": "Gênero da tia",
    "bisavo": "Gênero da bisavó",
    "primo": "Gênero do primo",
    "avo": "Gênero da avó",
    "avoh": "Gênero do avô",
}


def _gender_label(code: str | None) -> str | None:
    key = (code or "").strip().lower()
    if key == "f":
        return "Feminino"
    if key == "m":
        return "Masculino"
    return None


def _subject_label(code: str | None, gender: str | None) -> str | None:
    key = (code or "").strip().lower()
    if key == "primo" and (gender or "").strip().lower() == "f":
        return "Prima"
    return _SUBJECT.get(key)


def _one_line(raw: str | None, limit: int) -> str:
    return " ".join((raw or "").split())[:limit]


def client_registration(
    *,
    name: str | None,
    email: str | None,
    phone: str | None,
    address: str | None,
    notes: str | None = None,
) -> dict[str, str] | None:
    """Cadastro de quem compra. None quando nome, e-mail, telefone ou endereço falta."""
    record = {
        "name": _one_line(name, 120),
        "email": _one_line(email, 160),
        "phone": _one_line(phone, 40),
        "address": _one_line(address, 300),
        "notes": _one_line(notes, 500),
    }
    if not record["name"] or not record["phone"] or not record["address"]:
        return None
    if not _EMAIL.fullmatch(record["email"]):
        return None
    return record


def build_book_order_summary(
    *,
    style: str | None,
    child_name: str | None,
    language: str | None,
    theme: str | None,
    extra_names: list[str],
    photo_count: int,
    dedication: str | None = None,
    gender: str | None = None,
    subject: str | None = None,
    also_name: str | None = None,
    also_gender: str | None = None,
    also_subject: str | None = None,
    quantity: int | None = None,
    client_name: str | None = None,
    client_email: str | None = None,
    client_phone: str | None = None,
    client_address: str | None = None,
    client_notes: str | None = None,
) -> str:
    """Bloco exato que o dono vê. Cartoon só quando o estilo do livro é cartoon."""
    kind = "CARTOON" if (style or "").strip().lower() == "cartoon" else "REALISTA"
    child = " ".join((child_name or "").split())
    companion = " ".join((also_name or "").split())
    characters: list[str] = []
    seen: set[str] = set()
    if child:
        characters.append(child)
        seen.add(child.casefold())
    if companion and companion.casefold() not in seen:
        characters.append(companion)
        seen.add(companion.casefold())
    for name in extra_names:
        cleaned = " ".join(name.split())
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        characters.append(cleaned)
    count = max(int(photo_count), 0)
    if count == 1:
        photos = "1 (arquivo recebido)"
    else:
        photos = f"{count} (arquivos recebidos)"
    who = _subject_label(subject, gender)
    who_gender = _gender_label(gender)
    also_who_gender = _gender_label(also_gender)
    lines = [
        f"NOVO LIVRO STORY R US {kind}",
        f"Nome: {child or '—'}",
    ]
    if who:
        lines.append(f"Protagonista: {who}")
    if who_gender:
        lines.append(f"Gênero: {who_gender}")
    also_key = (also_subject or "").strip().lower()
    if also_key == "primo" and (also_gender or "").strip().lower() == "f":
        also_key = "prima"
    if companion:
        name_label = _ALSO_NAME.get(also_key, "Outro nome")
        if also_key == "prima":
            name_label = "Nome da prima"
        lines.append(f"{name_label}: {companion}")
    if also_who_gender:
        gender_label = _ALSO_GENDER.get(also_key, "Gênero")
        if also_key == "prima":
            gender_label = "Gênero da prima"
        lines.append(f"{gender_label}: {also_who_gender}")
    tail = [
        f"Idioma: {language_label(language)}",
        f"Tema: {(theme or '').strip() or '—'}",
    ]
    dedication_text = _one_line(dedication, 500)
    if dedication_text:
        tail.append(f"Dedicatória: {dedication_text}")
    tail.append(f"Personagens: {', '.join(characters) if characters else '—'}")
    copies = int(quantity) if isinstance(quantity, int) else None
    if copies is not None and 1 <= copies <= 500:
        tail.append(f"Quantidade: {copies}")
    tail.append(f"Fotos anexadas: {photos}")
    lines.extend(tail)
    buyer = client_registration(
        name=client_name,
        email=client_email,
        phone=client_phone,
        address=client_address,
        notes=client_notes,
    )
    if buyer is None:
        name = _one_line(client_name, 120)
        email = _one_line(client_email, 160)
        if name and _EMAIL.fullmatch(email):
            buyer = {"name": name, "email": email, "phone": "", "address": "", "notes": ""}
    if buyer:
        lines.append(f"Cliente: {buyer['name']}")
        lines.append(f"E-mail: {buyer['email']}")
        if buyer["phone"]:
            lines.append(f"Telefone: {buyer['phone']}")
        if buyer["address"]:
            lines.append(f"Endereço: {buyer['address']}")
        if buyer["notes"]:
            lines.append(f"Observação: {buyer['notes']}")
    return "\n".join(lines)
