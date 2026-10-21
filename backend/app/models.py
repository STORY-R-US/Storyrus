"""Modelo de dados.

Espelha o schema do documento de arquitetura (users, projects, jobs, assets),
com tipos portaveis (UUID/JSON) para rodar em Postgres (prod) e SQLite (testes).
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    CHAR,
    Boolean,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, TypeDecorator

from app.database import Base


# --------------------------------------------------------------------------- #
# Tipos portaveis
# --------------------------------------------------------------------------- #
class GUID(TypeDecorator):
    """UUID nativo no Postgres, CHAR(36) em outros bancos (ex.: SQLite)."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(str(value))
        return value if dialect.name == "postgresql" else str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


# JSONB no Postgres, JSON genérico no resto.
JSONType = JSON().with_variant(JSONB, "postgresql")


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(UTC)


# --------------------------------------------------------------------------- #
# Enums de dominio
# --------------------------------------------------------------------------- #
class ProjectStatus(str, enum.Enum):
    CREATED = "CREATED"
    AVATAR_RUNNING = "AVATAR_RUNNING"
    AVATAR_READY = "AVATAR_READY"
    STORY_RUNNING = "STORY_RUNNING"
    STORY_READY = "STORY_READY"
    EBOOK_RUNNING = "EBOOK_RUNNING"
    EBOOK_READY = "EBOOK_READY"
    VIDEO_RUNNING = "VIDEO_RUNNING"
    VIDEO_READY = "VIDEO_READY"
    FAILED = "FAILED"


class JobType(str, enum.Enum):
    AVATAR = "AVATAR"
    REALISTIC = "REALISTIC"
    STORY = "STORY"
    EBOOK = "EBOOK"
    STORYBOARD = "STORYBOARD"
    VIDEO = "VIDEO"
    NARRATED_VIDEO = "NARRATED_VIDEO"
    EXTRA_CHARACTER = "EXTRA_CHARACTER"


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


class AssetKind(str, enum.Enum):
    PHOTO = "photo"
    CHARACTER = "character"
    REALISTIC = "realistic_avatar"
    CHARACTER_SHEET = "character_sheet"
    EXPRESSION_SHEET = "expression_sheet"
    COSTUME_LOCK = "costume_lock"
    PAGE_IMAGE = "page_image"
    COVER = "cover"
    IN_HAND = "in_hand"
    EBOOK = "ebook"
    STORYBOARD = "storyboard"
    VIDEO = "video"
    NARRATED_VIDEO = "narrated_video"
    AUDIO = "audio"


class ProjectStyle(str, enum.Enum):
    CGI_3D = "cgi_3d"
    REALISTIC = "realistic"
    CARTOON = "cartoon"
    ANIME = "anime"


# --------------------------------------------------------------------------- #
# Tabelas
# --------------------------------------------------------------------------- #
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(default=_now, server_default=func.now())
    # Perfil (obrigatório no cadastro; nullable para guests / contas legadas).
    full_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    street: Mapped[str | None] = mapped_column(String(160), nullable=True)
    number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    complement: Mapped[str | None] = mapped_column(String(80), nullable=True)
    district: Mapped[str | None] = mapped_column(String(80), nullable=True)
    city: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # Estado/província/região (UF BR ou nome longo internacional).
    state: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # ISO 3166-1 alpha-2 (BR, US, PT…).
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    terms_accepted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # Painéis /gastos, /pedidos e /usuarios. Quem está em OWNER_EMAILS também
    # é promovido a admin no primeiro acesso autenticado.
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    email_verify_token_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    password_reset_token_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    projects: Mapped[list[Project]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    voices: Mapped[list[UserVoice]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserVoice(Base):
    """Voz clonada (ElevenLabs IVC) reutilizável pelo usuário."""

    __tablename__ = "user_voices"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    elevenlabs_voice_id: Mapped[str] = mapped_column(String(64), nullable=False)
    sample_storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False, default="audio/mpeg")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(default=_now, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="voices")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ProjectStatus.CREATED.value
    )
    style: Mapped[str | None] = mapped_column(String(16), nullable=True)
    theme: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Tamanho impresso escolhido na geração: M = 20×20 cm, P = 15×15 cm.
    book_size: Mapped[str | None] = mapped_column(String(1), nullable=True)
    # Acabamento escolhido na geração: soft = capa flexível, hard = capa dura.
    cover_type: Mapped[str | None] = mapped_column(String(4), nullable=True)
    # Segundo tema opcional: combinado com `theme` na mesma história (máx. 2 temas).
    # `theme` continua sendo o principal (define vilão/cenário/arco); `extra_theme`
    # só soma objetivo de aprendizado extra — ver handle_story.
    extra_theme: Mapped[str | None] = mapped_column(String(32), nullable=True)
    child_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # Idade da criança em anos (0-12); orienta tom, vocabulário e forma da história.
    child_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dedication: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Perfil educativo da crianca: traço central (o que a historia vai transformar) e
    # interesse/talento (a ferramenta que ela usa para superar o obstaculo no climax).
    child_trait: Mapped[str | None] = mapped_column(Text, nullable=True)
    child_interest: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Idioma do livro (BCP-47 simplificado: 'pt-BR', 'en'); None => pt-BR.
    language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    character_ref: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    # Personagens extras: lista de dicts [{name, storage_key, mime}].
    extra_characters: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    story_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ebook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    narrated_video_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    character_approved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    book_approved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # Quando o cliente foi avisado por e-mail que a prévia (história + imagens) ficou pronta.
    preview_notified_at: Mapped[datetime | None] = mapped_column(nullable=True)
    print_requested_at: Mapped[datetime | None] = mapped_column(nullable=True)
    print_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="projects")
    jobs: Mapped[list[Job]] = relationship(back_populates="project", cascade="all, delete-orphan")
    assets: Mapped[list[Asset]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    usage_events: Mapped[list["UsageEvent"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    order_ticket: Mapped["OrderTicket | None"] = relationship(
        back_populates="project", cascade="all, delete-orphan", uselist=False
    )
    print_order: Mapped["PrintOrder | None"] = relationship(
        back_populates="project", cascade="all, delete-orphan", uselist=False
    )


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_jobs_idempotency_key"),
        # Claim FIFO: WHERE status = PENDING ORDER BY created_at (STO-30).
        Index("ix_jobs_status_created_at", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=JobStatus.PENDING.value)
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # STO-29: correlacao API ↔ worker (mesmo id nos logs JSON + metadata Opik).
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    cost_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=_now, onupdate=_now, server_default=func.now()
    )

    project: Mapped[Project] = relationship(back_populates="jobs")
    usage_events: Mapped[list["UsageEvent"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class UsageEvent(Base):
    """Uma chamada de IA (imagem, texto, vídeo…) — linha do extrato."""

    __tablename__ = "usage_events"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=_uuid)
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=True, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="image")
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="gemini")
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now, server_default=func.now())

    job: Mapped[Job | None] = relationship(back_populates="usage_events")
    project: Mapped[Project] = relationship(back_populates="usage_events")


class OrderTicket(Base):
    """Pedido lido pelo dono depois que a família cria o livro e a foto chega."""

    __tablename__ = "order_tickets"
    __table_args__ = (UniqueConstraint("project_id", name="uq_order_tickets_project_id"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=_now, server_default=func.now())

    project: Mapped[Project] = relationship(back_populates="order_ticket")


class PrintOrder(Base):
    """Pedido do livro impresso, separado do resumo que a família envia com a foto."""

    __tablename__ = "print_orders"
    __table_args__ = (
        UniqueConstraint("project_id", name="uq_print_orders_project_id"),
        UniqueConstraint("code", name="uq_print_orders_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    book_size: Mapped[str | None] = mapped_column(String(1), nullable=True)
    cover_type: Mapped[str | None] = mapped_column(String(8), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # awaiting_spec | awaiting_pages | held | files_ready |
    # sent_for_validation | approved | rejected
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="awaiting_spec")
    block_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    interior_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    recipient_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    street: Mapped[str | None] = mapped_column(String(160), nullable=True)
    number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    complement: Mapped[str | None] = mapped_column(String(80), nullable=True)
    district: Mapped[str | None] = mapped_column(String(80), nullable=True)
    city: Mapped[str | None] = mapped_column(String(80), nullable=True)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    freight_options: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    freight_service_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    freight_service_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    freight_price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    freight_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payment_status: Mapped[str] = mapped_column(String(16), nullable=False, default="unpaid")
    payment_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payment_reference: Mapped[str | None] = mapped_column(String(80), nullable=True)
    amount_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tracking_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    label_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    label_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=_now, onupdate=_now, server_default=func.now()
    )

    project: Mapped[Project] = relationship(back_populates="print_order")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now, server_default=func.now())

    project: Mapped[Project] = relationship(back_populates="assets")
