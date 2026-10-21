"""Extração de texto de arquivos de história (PDF, DOCX, DOC, TXT).

Usado quando o usuário prefere enviar a própria história em vez de a IA inventar.
"""

from __future__ import annotations

import io


def extract_text(filename: str, data: bytes) -> str:
    name = (filename or "").lower()
    if name.endswith(".txt"):
        return _decode(data)
    if name.endswith(".pdf"):
        return _pdf(data)
    if name.endswith(".docx"):
        return _docx(data)
    if name.endswith(".doc"):
        # .doc binário antigo: melhor esforço (sem dependência pesada).
        return _decode(data)
    # Sem extensão reconhecida: tenta detectar pelo conteúdo.
    if data[:4] == b"%PDF":
        return _pdf(data)
    if data[:2] == b"PK":  # zip → provavelmente docx
        try:
            return _docx(data)
        except Exception:
            pass
    return _decode(data)


def _decode(data: bytes) -> str:
    for enc in ("utf-8", "latin-1"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", errors="ignore")


def _pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return "\n\n".join((page.extract_text() or "") for page in reader.pages).strip()


def _docx(data: bytes) -> str:
    import docx

    document = docx.Document(io.BytesIO(data))
    return "\n".join(p.text for p in document.paragraphs).strip()
