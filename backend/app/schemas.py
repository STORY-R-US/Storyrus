"""DTOs de entrada/saida (Pydantic v2)."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from pydantic_core import PydanticCustomError

from app.models import JobType, ProjectStyle


# ---- Auth ----
def _norm_region(value: str) -> str:
    """UF curta em maiúsculas; região/estado internacional preserva o texto."""
    cleaned = value.strip()
    if len(cleaned) <= 3:
        return cleaned.upper()
    return cleaned


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    password_confirm: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=8, max_length=32)
    # CEP BR (8) ou ZIP/postal internacional (ex. US 5, UK alfanumérico).
    postal_code: str = Field(min_length=2, max_length=16)
    street: str = Field(min_length=1, max_length=160)
    number: str = Field(min_length=1, max_length=20)
    complement: str | None = Field(default=None, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    city: str = Field(min_length=1, max_length=80)
    state: str = Field(min_length=1, max_length=80)
    country: str = Field(min_length=2, max_length=2)
    accept_terms: bool

    @model_validator(mode="after")
    def _passwords_and_terms(self) -> "SignupIn":
        if self.password != self.password_confirm:
            raise PydanticCustomError("password_mismatch", "As senhas nao coincidem")
        if not self.accept_terms:
            raise PydanticCustomError(
                "terms_required", "Aceite os termos e a politica de privacidade"
            )
        self.country = self.country.strip().upper()
        if not self.country.isalpha():
            raise PydanticCustomError("country_invalid", "Codigo de pais invalido")
        self.postal_code = self.postal_code.strip()
        self.state = _norm_region(self.state)
        if self.district is not None:
            district = self.district.strip()
            self.district = district or None
        if self.complement is not None:
            complement = self.complement.strip()
            self.complement = complement or None
        return self


class SignupOut(BaseModel):
    ok: bool = True
    message: str
    # Só fora de prod (testes / local).
    verify_token: str | None = None


class VerifyEmailIn(BaseModel):
    token: str = Field(min_length=20, max_length=4096)


class ResendVerifyIn(BaseModel):
    email: EmailStr


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ForgotPasswordOut(BaseModel):
    ok: bool = True
    message: str
    # Só fora de prod (testes / local).
    reset_token: str | None = None


class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=20, max_length=4096)
    password: str = Field(min_length=8, max_length=128)
    password_confirm: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def _passwords_match(self) -> "ResetPasswordIn":
        if self.password != self.password_confirm:
            raise PydanticCustomError("password_mismatch", "As senhas nao coincidem")
        return self


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ProfileUpdateIn(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    accept_terms: bool | None = None
    confirm_adult: bool | None = None
    phone: str | None = Field(default=None, min_length=8, max_length=32)
    postal_code: str | None = Field(default=None, min_length=2, max_length=16)
    street: str | None = Field(default=None, min_length=1, max_length=160)
    number: str | None = Field(default=None, min_length=1, max_length=20)
    complement: str | None = Field(default=None, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    city: str | None = Field(default=None, min_length=1, max_length=80)
    state: str | None = Field(default=None, min_length=1, max_length=80)
    country: str | None = Field(default=None, min_length=2, max_length=2)

    @model_validator(mode="after")
    def _norm_address(self) -> "ProfileUpdateIn":
        if self.country is not None:
            self.country = self.country.strip().upper()
            if not self.country.isalpha():
                raise PydanticCustomError("country_invalid", "Codigo de pais invalido")
        if self.postal_code is not None:
            self.postal_code = self.postal_code.strip()
        if self.state is not None:
            self.state = _norm_region(self.state)
        if self.district is not None:
            district = self.district.strip()
            self.district = district or None
        if self.complement is not None:
            complement = self.complement.strip()
            self.complement = complement or None
        return self


class ResumeIn(BaseModel):
    """JWT expirado (ou quase) para reemitir sessao sem criar usuario novo."""

    access_token: str = Field(min_length=20, max_length=4096)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: EmailStr
    credits: int
    created_at: datetime
    is_guest: bool = False
    email_verified: bool = False
    is_admin: bool = False
    is_owner: bool = False
    full_name: str | None = None
    phone: str | None = None
    postal_code: str | None = None
    street: str | None = None
    number: str | None = None
    complement: str | None = None
    district: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    terms_accepted_at: datetime | None = None
    adult_confirmed_at: datetime | None = None


class OwnerUserOut(BaseModel):
    """Conta cadastrada no painel do dono (sem convidados)."""

    id: uuid.UUID
    email: EmailStr
    credits: int
    created_at: datetime
    project_count: int = 0
    full_name: str | None = None
    phone: str | None = None
    email_verified: bool = False
    postal_code: str | None = None
    street: str | None = None
    number: str | None = None
    complement: str | None = None
    district: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    terms_accepted_at: datetime | None = None
    is_admin: bool = False
    adult_confirmed: bool = False


class OwnerUserUpdateIn(ProfileUpdateIn):
    """Campos opcionais para o dono editar uma conta cadastrada."""

    email: EmailStr | None = None
    credits: int | None = Field(default=None, ge=0, le=100_000)
    email_verified: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    is_admin: bool | None = None
    adult_confirmed: bool | None = None

    @model_validator(mode="after")
    def _has_patch(self) -> "OwnerUserUpdateIn":
        if not self.model_dump(exclude_unset=True):
            raise PydanticCustomError("empty_patch", "Nada para atualizar")
        return self


class OwnerUsersOut(BaseModel):
    total: int
    users: list[OwnerUserOut]


# ---- Projects ----
class ProjectCreateIn(BaseModel):
    theme_description: str | None = Field(default=None, max_length=500)
    characters: str | None = Field(default=None, max_length=500)
    title: str | None = Field(default=None, max_length=120)
    gender: str | None = Field(default=None, pattern="^(f|m)$")
    languages: list[Literal["pt-BR", "en", "es"]] | None = Field(
        default=None, min_length=1, max_length=3
    )
    style: ProjectStyle = ProjectStyle.CGI_3D
    # Tema narrativo da história (aventura, princesas, espaco, ...). Aberto por design.
    theme: str | None = Field(default=None, max_length=32)
    # M = 20×20 cm, P = 15×15 cm. Vazio mantém o miolo atual.
    book_size: str | None = Field(default=None, pattern="^(M|P)$")
    # soft = capa flexível, hard = capa dura.
    cover_type: str | None = Field(default=None, pattern="^(soft|hard)$")
    # Segundo tema opcional (máx. 2 na mesma história): `theme` continua definindo
    # vilão/cenário/arco; `extra_theme` só soma um objetivo de aprendizado extra.
    extra_theme: str | None = Field(default=None, max_length=32)
    child_name: str | None = Field(default=None, max_length=80)
    # Idade da criança em anos; guia tom, vocabulário e complexidade da história.
    child_age: int | None = Field(default=None, ge=0, le=120)
    dedication: str | None = Field(default=None, max_length=500)
    # Traço central: o ponto de partida que a história vai transformar (ex.: "tem medo
    # do escuro", "não gosta de dividir os brinquedos"). Deve apontar para o tema/objetivo
    # educacional escolhido.
    child_trait: str | None = Field(default=None, max_length=300)
    # Interesse/talento: a ferramenta que a criança usa para vencer o obstáculo no clímax
    # (ex.: "adora dinossauros", "é curiosa e observadora").
    child_interest: str | None = Field(default=None, max_length=300)
    # Idioma do livro: 'pt-BR' (padrao) ou 'en'.
    language: str | None = Field(default="pt-BR", max_length=8)


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    status: str
    style: str | None
    theme: str | None
    book_size: str | None = None
    cover_type: str | None = None
    extra_theme: str | None = None
    child_name: str | None
    child_age: int | None
    dedication: str | None
    child_trait: str | None = None
    child_interest: str | None = None
    language: str | None
    book_profile: dict | None = None
    extra_characters: list[dict] | None = None
    story_text: str | None
    ebook_url: str | None
    video_url: str | None
    narrated_video_url: str | None = None
    character_approved_at: datetime | None = None
    book_approved_at: datetime | None = None
    purchase_flow: dict | None = None
    print_requested_at: datetime | None = None
    print_status: str | None = None
    created_at: datetime


class UploadUrlIn(BaseModel):
    content_type: str = "image/jpeg"
    ext: str = "jpg"


class UploadUrlOut(BaseModel):
    asset_id: uuid.UUID
    storage_key: str
    upload_url: str
    expires_in: int


class VideoRequestIn(BaseModel):
    """Pedido de Animação (Kling image2video). Duração: 5 ou 10 segundos."""

    duration_s: int = Field(default=5, ge=5, le=10)
    provider: str | None = None


class NarratedVideoRequestIn(BaseModel):
    """Pedido de vídeo narrado (TTS + montagem). voice_id = UUID interno de UserVoice."""

    voice_id: uuid.UUID | None = None


class StoryTextIn(BaseModel):
    """História fornecida pelo usuário (digitada ou colada de um arquivo)."""

    story_text: str = Field(min_length=1, max_length=20000)


class StoryRequestIn(BaseModel):
    """Pedido de história com IA (brief opcional do formulário do Studio)."""

    brief: str | None = Field(default=None, max_length=2000)


class PreviewRequestIn(BaseModel):
    image: Literal["01_CAPA", "02_LIVRO_ABERTO", "03_LEITURA"] | None = None
    language: Literal["pt-BR", "en", "es"] | None = None
    adjustment: str | None = Field(default=None, max_length=500)
    """Dispara a cadeia automática de prévia (avatar → história → ebook → vídeo)."""

    brief: str | None = Field(default=None, max_length=2000)


class StoryExtractOut(BaseModel):
    """Texto extraído de um arquivo enviado (PDF/DOCX/TXT)."""

    text: str


class StoryTemplateOut(BaseModel):
    """Metadados de uma história pronta do catálogo (templates traduzidos)."""

    id: str
    titulo: str
    genero: str
    idade: str
    tematica: str
    emoji: str
    paginas: int


class StoryTemplateApplyIn(BaseModel):
    """Aplicar uma história pronta do catálogo ao projeto (sem IA, sem créditos)."""

    template_id: str = Field(min_length=1, max_length=64)
    gender: str | None = Field(default=None, max_length=16)


# ---- Jobs ----
class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    type: str
    status: str
    provider: str | None
    cost_credits: int
    cost_usd: float | None = None
    attempts: int
    error: str | None
    request_id: str | None = None
    created_at: datetime
    result: dict | None = None


class JobAcceptedOut(BaseModel):
    """Resposta 202 padrao para etapas assincronas."""

    job_id: uuid.UUID
    status: str
    type: JobType
    estimated_cost_credits: int
    request_id: str | None = None


# ---- Credits ----
class CreditGrantIn(BaseModel):
    amount: int = Field(gt=0, le=100000)


class CreditsOut(BaseModel):
    credits: int


class UsageBucketOut(BaseModel):
    key: str
    usd: float
    jobs: int


class UsageBookOut(BaseModel):
    project_id: uuid.UUID
    child_name: str | None
    status: str
    usd: float | None
    unmeasured_jobs: int
    updated_at: datetime


class UsageJobOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    child_name: str | None
    type: str
    status: str
    provider: str | None
    cost_usd: float | None
    attempts: int
    created_at: datetime


class UsageEventOut(BaseModel):
    id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None
    project_id: uuid.UUID
    child_name: str | None
    kind: str
    provider: str
    action: str
    label: str
    cost_usd: float | None
    created_at: datetime


class UsageAnomalyOut(BaseModel):
    kind: str
    severity: str
    message: str


class OrderFileOut(BaseModel):
    """Arquivo do livro guardado no storage e ligado à OS."""

    label: str
    url: str
    kind: str | None = None
    provider: str | None = None


class OrderTicketOut(BaseModel):
    """Resumo do pedido. As fotos vão como links assinados, gerados na hora da leitura."""

    id: uuid.UUID
    project_id: uuid.UUID
    summary: str
    created_at: datetime
    child_age: int | None = None
    book_size: str | None = None
    cover_type: str | None = None
    style: str | None = None
    photo_urls: list[str] = []
    has_story: bool = False
    book_files: list[OrderFileOut] = []
    generation_status: str = "queued"
    generation_stage: str | None = None
    generated_images: int = 0
    image_provider: str | None = None
    image_model: str | None = None
    generation_error: str | None = None
    credits_fallback: bool = False
    print_order_id: uuid.UUID | None = None
    print_code: str | None = None
    print_status: str | None = None
    block_reason: str | None = None
    tracking_code: str | None = None
    payment_status: str | None = None
    amount_cents: int | None = None
    account_email: str | None = None
    mine: bool = False
    child_name: str | None = None
    dedication: str | None = None
    quantity: int | None = None
    recipient_name: str | None = None
    postal_code: str | None = None
    street: str | None = None
    number: str | None = None
    complement: str | None = None
    district: str | None = None
    city: str | None = None
    state: str | None = None


class OrderEditIn(BaseModel):
    """O admin corrige o pedido sem passar pelo estúdio da família."""

    child_name: str | None = Field(default=None, max_length=80)
    child_age: int | None = Field(default=None, ge=0, le=120)
    dedication: str | None = Field(default=None, max_length=500)
    book_size: Literal["M", "P"] | None = None
    cover_type: Literal["soft", "hard"] | None = None
    quantity: int | None = Field(default=None, ge=1, le=20)
    payment_status: Literal["unpaid", "pending", "paid"] | None = None
    tracking_code: str | None = Field(default=None, max_length=40)
    recipient_name: str | None = Field(default=None, max_length=120)
    postal_code: str | None = Field(default=None, max_length=16)
    street: str | None = Field(default=None, max_length=160)
    number: str | None = Field(default=None, max_length=20)
    complement: str | None = Field(default=None, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    city: str | None = Field(default=None, max_length=80)
    state: str | None = Field(default=None, max_length=2)

    @model_validator(mode="after")
    def _has_patch(self) -> "OrderEditIn":
        if not self.model_dump(exclude_unset=True):
            raise PydanticCustomError("empty_patch", "Nada para atualizar")
        return self


class FreightOptionOut(BaseModel):
    service_id: int
    service_name: str
    price_cents: int
    delivery_days: int | None = None


class PrintAddressIn(BaseModel):
    recipient_name: str = Field(min_length=1, max_length=120)
    postal_code: str = Field(min_length=8, max_length=16)
    street: str = Field(min_length=1, max_length=160)
    number: str = Field(min_length=1, max_length=20)
    complement: str | None = Field(default=None, max_length=80)
    district: str = Field(min_length=1, max_length=80)
    city: str = Field(min_length=1, max_length=80)
    state: str = Field(min_length=2, max_length=2)


class FreightSelectIn(BaseModel):
    service_id: int


class PrintQuantityIn(BaseModel):
    quantity: int = Field(ge=1, le=500)


class PrintCheckoutIn(BaseModel):
    installments: int = Field(default=1, ge=1, le=12)


class PrintValidationIn(BaseModel):
    status: str = Field(pattern="^(sent_for_validation|approved|rejected)$")


class PrintOrderOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    code: str
    book_size: str | None = None
    cover_type: str | None = None
    quantity: int
    status: str
    block_reason: str | None = None
    book_price_cents: int | None = None
    freight_options: list[FreightOptionOut] = []
    freight_service_id: int | None = None
    freight_service_name: str | None = None
    freight_price_cents: int | None = None
    freight_days: int | None = None
    payment_status: str
    amount_cents: int | None = None
    tracking_code: str | None = None
    label_error: str | None = None
    checkout_available: bool = False
    checkout_url: str | None = None
    recipient_name: str | None = None
    postal_code: str | None = None
    street: str | None = None
    number: str | None = None
    complement: str | None = None
    district: str | None = None
    city: str | None = None
    state: str | None = None


class ErrorReportOut(BaseModel):
    created_at: datetime
    project_id: uuid.UUID | None = None
    child_name: str | None = None
    stage: str
    message: str


class UsageOut(BaseModel):
    timezone: str
    from_at: datetime
    to_at: datetime
    today_usd: float
    month_usd: float
    range_usd: float
    books_count: int
    avg_book_usd: float | None
    by_type: list[UsageBucketOut]
    by_provider: list[UsageBucketOut]
    books: list[UsageBookOut]
    recent_jobs: list[UsageJobOut]
    events: list[UsageEventOut] = []
    events_count: int = 0
    # STO-18: tetos + anomalias (opcional; 0/None = desligado).
    daily_spend_usd_ceiling: float | None = None
    daily_credits_ceiling: int | None = None
    today_credits: int = 0
    reserved_usd: float = 0.0
    anomalies: list[UsageAnomalyOut] = []
    orders: list[OrderTicketOut] = []
    # Diagnóstico do painel Pedidos: cadastros/projetos sem pedido com foto.
    users_total: int = 0
    projects_total: int = 0
    projects_awaiting_photo: int = 0
    error_report: list[ErrorReportOut] = []
