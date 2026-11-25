"""Ajuda de IA no formulário do Estúdio, antes de o projeto existir."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.deps import require_adult_user
from app.models import User

router = APIRouter(prefix="/v1/studio", tags=["studio"])


class DedicationIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    name: str = Field(default="", max_length=80)
    language: str = Field(default="pt-BR", max_length=10)


class DedicationOut(BaseModel):
    dedication: str


@router.post("/dedication/improve", response_model=DedicationOut)
async def improve_dedication(body: DedicationIn, user: User = Depends(require_adult_user)):
    """Melhora a dedicatória que a família escreveu. Não altera nenhum projeto."""
    from app.ai_clients import get_text_provider
    from app.ai_clients.base import ProviderError
    from app.rate_limit import allow

    text = " ".join(body.text.split())
    if not text:
        raise HTTPException(422, "Escreva a dedicatória antes de pedir para melhorar.")
    if not allow(f"dedication-improve:{user.id}", 10, 3600):
        raise HTTPException(429, "Limite de melhorias atingido. Tente novamente mais tarde.")
    language = body.language if body.language in {"pt-BR", "en", "es"} else "pt-BR"
    try:
        dedication = await get_text_provider().improve_dedication(
            text=text, name=body.name.strip(), language=language
        )
    except ProviderError as exc:
        raise HTTPException(502, "Não foi possível melhorar a dedicatória agora.") from exc
    return DedicationOut(dedication=dedication)


def _language(value: str) -> str:
    return value if value in {"pt-BR", "en", "es"} else "pt-BR"


class StudioTitleIn(BaseModel):
    theme: str = Field(default="", max_length=500)
    title: str = Field(default="", max_length=120)
    name: str = Field(default="", max_length=80)
    age: int | None = Field(default=None, ge=0, le=120)
    language: str = Field(default="pt-BR", max_length=10)


class StudioTitleOut(BaseModel):
    titles: list[str]


@router.post("/title/suggest", response_model=StudioTitleOut)
async def suggest_studio_titles(body: StudioTitleIn, user: User = Depends(require_adult_user)):
    """Sugere 5 títulos a partir do tema digitado no Estúdio. Não altera nenhum projeto."""
    from app.ai_clients import get_text_provider
    from app.ai_clients.base import ProviderError
    from app.rate_limit import allow

    theme = " ".join(body.theme.split())
    title = " ".join(body.title.split())
    if not theme and not title:
        raise HTTPException(422, "Escreva o tema da história antes de pedir um título.")
    if not allow(f"studio-title:{user.id}", 10, 3600):
        raise HTTPException(429, "Limite de sugestões atingido. Tente novamente mais tarde.")
    context = {
        "title": title,
        "theme": theme,
        "protagonist": body.name.strip(),
        "age": body.age,
        "language": _language(body.language),
        "story": "",
    }
    try:
        titles = await get_text_provider().suggest_titles(context=context)
    except ProviderError as exc:
        raise HTTPException(502, "Não foi possível sugerir títulos agora.") from exc
    return StudioTitleOut(titles=titles)


class DedicationSuggestIn(BaseModel):
    name: str = Field(default="", max_length=80)
    age: int | None = Field(default=None, ge=0, le=120)
    theme: str = Field(default="", max_length=500)
    title: str = Field(default="", max_length=120)
    draft: str = Field(default="", max_length=500)
    language: str = Field(default="pt-BR", max_length=10)


class DedicationSuggestOut(BaseModel):
    dedications: list[str]


@router.post("/dedication/suggest", response_model=DedicationSuggestOut)
async def suggest_dedications(body: DedicationSuggestIn, user: User = Depends(require_adult_user)):
    """Escreve 3 dedicatórias que entendem o tema e o título do livro. Não altera projetos."""
    from app.ai_clients import get_text_provider
    from app.ai_clients.base import ProviderError
    from app.rate_limit import allow

    context = {
        "child_name": body.name.strip(),
        "age": body.age,
        "theme": " ".join(body.theme.split()),
        "title": " ".join(body.title.split()),
        "draft": " ".join(body.draft.split()),
        "language": _language(body.language),
    }
    if not context["theme"] and not context["title"] and not context["child_name"]:
        raise HTTPException(422, "Preencha o nome ou o tema antes de pedir uma dedicatória.")
    if not allow(f"dedication-suggest:{user.id}", 10, 3600):
        raise HTTPException(429, "Limite de sugestões atingido. Tente novamente mais tarde.")
    try:
        dedications = await get_text_provider().write_dedications(context=context)
    except ProviderError as exc:
        raise HTTPException(502, "Não foi possível sugerir dedicatórias agora.") from exc
    return DedicationSuggestOut(dedications=dedications)
