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
