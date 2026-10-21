"""Interfaces dos provedores de IA.

A camada de abstracao isola o pipeline do provedor concreto: hoje o video e
somente Kling (`video_kling.KlingVideoProvider`); imagem e Nano Banana (com
lane Fal). Trocar de provedor e registrar outra implementacao na factory, nao
mudar o fluxo dos handlers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


class ProviderError(Exception):
    """Erro recuperavel/irrecuperavel de provedor. `transient=True` -> elegivel a retry."""

    def __init__(self, message: str, *, transient: bool = False, status_code: int | None = None):
        super().__init__(message)
        self.transient = transient
        self.status_code = status_code


class CreditsExhaustedError(ProviderError):
    """Conta do provedor sem credito. Nao e rate limit: nao adianta esperar."""

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message, transient=False, status_code=status_code)


# --------------------------------------------------------------------------- #
# Resultados
# --------------------------------------------------------------------------- #
@dataclass
class ImageResult:
    image_bytes: bytes
    mime_type: str = "image/png"
    cost_usd: float | None = None
    meta: dict = field(default_factory=dict)


@dataclass
class TextResult:
    text: str
    cost_usd: float | None = None
    meta: dict = field(default_factory=dict)


@dataclass
class VideoJob:
    """Video e assincrono: o provedor devolve um id de tarefa; o resultado vem por polling/callback."""

    provider_task_id: str
    status: str = "PENDING"  # PENDING | RUNNING | DONE | FAILED
    video_url: str | None = None
    cost_usd: float | None = None
    meta: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Interfaces
# --------------------------------------------------------------------------- #
@runtime_checkable
class ImageProvider(Protocol):
    name: str

    async def generate_character(
        self, *, prompt: str, reference_images: list[bytes], style: str
    ) -> ImageResult:
        """Gera o personagem 2D a partir das fotos (etapa 2)."""

    async def generate_scene(
        self,
        *,
        prompt: str,
        character_ref: bytes,
        style: str,
        photo: bytes | None = None,
        extra_refs: list[bytes] | None = None,
        reference_role: str = "character",
    ) -> ImageResult:
        """Gera uma ilustracao de pagina reutilizando o avatar (`character_ref`).

        `photo` e aceito por compatibilidade e ignorado: a foto real so entra
        no lock do avatar / face-swap, nao na geracao da cena.
        """

    async def generate_realistic(
        self, *, photo: bytes, prompt: str, negative: str = "", style: str = "realistic"
    ) -> ImageResult:
        """Gera a versao realistica/ilustrada a partir da foto, com prompt customizado."""

    async def refine_identity(
        self, *, photo: bytes, illustration: bytes, style: str = "realistic"
    ) -> ImageResult:
        """Segundo passe: corrige a ilustracao para ficar fiel a foto real (opcional)."""

    async def refine_scene(
        self,
        *,
        character_ref: bytes,
        scene: bytes,
        style: str = "realistic",
        photo: bytes | None = None,
    ) -> ImageResult:
        """Segundo passe de cena: corrige o protagonista para bater com o personagem (opcional)."""


@runtime_checkable
class TextProvider(Protocol):
    name: str

    async def generate_story(
        self,
        *,
        brief: str,
        style: str,
        pages: int,
        language: str = "pt-BR",
        age: int | None = None,
    ) -> TextResult:
        """Gera a historia personalizada (etapas 5-8) no idioma e idade pedidos."""

    async def summarize_pages(
        self, *, pages: list[str], style: str = "", language: str = "pt-BR"
    ) -> list[str]:
        """Resume cada pagina em uma legenda curta, no idioma pedido."""


@runtime_checkable
class VideoProvider(Protocol):
    name: str

    async def create_video(self, *, image: bytes, prompt: str, duration_s: int) -> VideoJob:
        """Cria a tarefa (assincrona) de video a partir de uma imagem de referencia."""

    async def poll_video(self, *, provider_task_id: str) -> VideoJob:
        """Consulta o status/resultado de uma tarefa de video."""
