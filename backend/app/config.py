"""Configuracao central da aplicacao (12-factor: tudo via ambiente)."""

from functools import lru_cache
from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Defaults inseguros: fora de `dev` a API/worker recusam subir com estes valores.
_UNSAFE_SECRET_VALUES = frozenset(
    {
        "",
        "change-me",
        "change-me-in-prod",
        "change-me-webhook",
        "changeme",
        "secret",
        "password",
    }
)


def _is_unsafe_secret(value: str | None) -> bool:
    if value is None:
        return False
    cleaned = value.strip()
    if not cleaned:
        return True
    low = cleaned.lower()
    if low in _UNSAFE_SECRET_VALUES:
        return True
    return low.startswith("change-me")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: Literal["dev", "staging", "prod"] = "dev"
    app_name: str = "storyrus-api"
    log_level: str = "INFO"
    # text = legivel local; json = uma linha JSON (prod / Render). Vazio = auto
    # (json fora de dev).
    log_format: Literal["text", "json", "auto"] = "auto"

    # Banco / fila
    database_url: str = "sqlite+pysqlite:///./dev.db"
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    jwt_secret: str = "change-me-in-prod"
    jwt_algorithm: str = "HS256"
    access_token_ttl_min: int = 60 * 24
    # Janela extra apos o exp do JWT em que POST /v1/auth/resume ainda reemite
    # o mesmo user_id (evita projetos orfaos de guest). 0 = so tokens validos.
    guest_resume_grace_min: int = 60 * 24 * 30
    # Vazio / default = POST /v1/credits/grant recusa. Nao exponha no front.
    credit_grant_secret: str = ""
    # Anti-farming em POST /v1/auth/guest (0 = desliga aquele eixo).
    guest_rate_limit_per_ip: int = 10
    guest_rate_limit_per_fingerprint: int = 5
    guest_rate_limit_window_s: int = 3600
    # Verificação de e-mail + envio (Resend opcional).
    email_verify_ttl_min: int = 60 * 24
    # Redefinição de senha (JWT purpose=password_reset).
    password_reset_ttl_min: int = 60
    password_reset_rate_limit_per_ip: int = 8
    password_reset_rate_limit_per_email: int = 3
    password_reset_rate_limit_window_s: int = 3600
    public_web_origin: str = "https://storyrus.ai"
    resend_api_key: str = ""
    # Env vazio no Render (sync:false sem valor) não pode sobrescrever o from.
    transactional_from_email: str = "Story R Us <noreply@storyrus.ai>"

    # Storage (R2/S3)
    storage_bucket: str = "stories-dev"
    storage_endpoint_url: str | None = None  # R2/MinIO; None = AWS S3 padrao
    # Endpoint visto pelo navegador para URLs assinadas (presign). Em dev local
    # com MinIO: containers usam http://minio:9000 e o navegador http://localhost:9000.
    storage_public_endpoint_url: str | None = None
    storage_region: str = "auto"
    storage_access_key: str | None = None
    storage_secret_key: str | None = None
    storage_signing_ttl: int = 600  # segundos
    # Sem STORAGE_ACCESS_KEY/SECRET: disco local (dev/host sem R2).
    storage_local_dir: str = ".local-storage"

    # Politica de negocio
    # Limite de jobs PENDING/RUNNING por usuario (inclui VIDEO / NARRATED_VIDEO).
    max_concurrent_jobs_per_user: int = 4
    # Kling image2video aceita só 5s ou 10s; default alinhado ao provedor.
    default_video_duration_s: int = 5
    signup_bonus_credits: int = 10
    # false = gerar o livro não debita nem bloqueia por saldo. A cobrança é a OS do impresso.
    credits_enabled: bool = False
    offline_fallback: bool = True

    # Custo estimado por etapa (creditos = 1 credito ~ 1 unidade de custo)
    cost_avatar_credits: int = 1
    cost_story_credits: int = 1
    cost_ebook_credits: int = 1
    cost_video_credits: int = 5
    cost_narrated_video_credits: int = 8

    # Painel admin (USD real). A conta do dono entra com o JWT mesmo se
    # OWNER_EMAILS no Render estiver vazio. Sem senha e sem e-mail de dono,
    # /v1/usage responde 503.
    usage_dashboard_password: str | None = None
    # Senha anterior aceita durante rotacao (grace). Vazio = so a atual.
    usage_dashboard_password_previous: str | None = None
    # E-mails do dono (csv) que acessam /gastos /pedidos /usuarios com o JWT
    # e são gravados como users.is_admin no primeiro acesso.
    # Default: conta do André; override via OWNER_EMAILS no Render se precisar.
    owner_emails: str = "eng.andrevitor89@gmail.com"
    # true = a senha compartilhada (X-Usage-Password) ainda abre os painéis.
    # false = só conta com is_admin (ou e-mail em OWNER_EMAILS).
    owner_password_fallback: bool = True
    # Lockout apos N senhas erradas por IP (0 = desliga). Janela em segundos.
    usage_lockout_max_attempts: int = 5
    usage_lockout_window_s: int = 900
    # Teto diario da plataforma (America/Sao_Paulo). 0 = desligado.
    daily_spend_usd_ceiling: float = 0.0
    daily_credits_ceiling: int = 0
    # Alarmes no /gastos: razao do teto USD e piso absoluto opcional.
    spend_anomaly_warn_ratio: float = 0.8
    spend_anomaly_usd: float = 0.0
    price_claude_input_per_mtok: float = 15.0
    price_claude_output_per_mtok: float = 75.0
    price_kling_per_second_usd: float = 0.10
    price_openai_image_usd: float = 0.04

    # Impresso. Milímetros, perfil e pacote ficam vazios até a gráfica e a Ana
    # enviarem os números. Preço atual da vitrine: P R$ 157, M R$ 177.
    print_bleed_mm: float | None = None
    print_safety_mm: float | None = None
    print_spine_mm: float | None = None
    print_score_mm: float | None = None
    print_pdf_x: str | None = None
    print_color_profile: str | None = None
    print_filename_pattern: str | None = None
    print_package_weight_g: int | None = None
    print_package_height_cm: float | None = None
    print_package_width_cm: float | None = None
    print_package_length_cm: float | None = None
    print_price_p_cents: int = 15700
    print_price_m_cents: int = 17700
    print_allow_p_hardcover: bool = False
    print_gateway: str = ""
    melhor_envio_token: str = ""
    melhor_envio_sandbox: bool = True
    melhor_envio_from_postal_code: str = ""
    melhor_envio_from_name: str = ""
    melhor_envio_from_address: str = ""
    melhor_envio_from_number: str = ""
    melhor_envio_from_district: str = ""
    melhor_envio_from_city: str = ""
    melhor_envio_from_state: str = ""
    melhor_envio_user_agent: str = "StoryUS (info@storyrus.ai)"

    # Webhooks
    webhook_signing_secret: str = "change-me-webhook"
    # Janela anti-replay: |now - X-Timestamp| nao pode exceder isto (segundos).
    webhook_max_age_s: float = 300.0

    # Provedores de IA
    anthropic_api_key: str | None = None  # historia (Claude)
    # Video Kling: preferir KLING_API_KEY (Bearer novo). AK/SK = legado JWT.
    kling_api_key: str | None = None
    kling_access_key: str | None = None
    kling_secret_key: str | None = None
    elevenlabs_api_key: str | None = None  # TTS video narrado
    elevenlabs_voice_id: str | None = None  # voz ElevenLabs (default interno se vazio)
    openai_api_key: str | None = None  # GPT Image + juiz de historia
    openai_image_model: str = "gpt-image-1"
    openai_image_size_portrait: str = "1024x1536"
    openai_image_size_square: str = "1024x1024"
    openai_timeout_s: float = 120.0
    openai_max_retries: int = 3
    openai_retry_base_s: float = 2.0
    openai_retry_max_s: float = 60.0
    openai_story_judge_model: str = "gpt-4o-mini"
    # Retries do juiz de rosto (InsightFace) no avatar/paginas.
    face_match_retries: int = 3
    # TLS do cliente Opik: true | system | false
    opik_ssl_verify: str = "true"

    # Selecao de provedores por etapa
    image_provider: str = "openai"
    text_provider: str = "claude"
    # Unico VideoProvider registrado: Kling. Outros nomes falham na factory.
    video_provider: str = "kling"

    # Workers
    worker_poll_interval_s: float = 2.0
    worker_batch_size: int = 5
    job_max_attempts: int = 5
    retry_backoff_base_s: float = 2.0
    retry_backoff_max_s: float = 60.0
    # Sem heartbeat por este tempo => RUNNING volta a PENDING (worker morreu).
    job_stale_timeout_s: float = 900.0
    # Prévia parada em RUNNING (worker que morreu) volta bem antes das 15 min.
    preview_stale_timeout_s: float = 180.0
    # Cada figura da prévia (capa, página, na mão) tem um teto. Estourar o tempo
    # não reinicia o livro: a prévia fecha com as imagens que já saíram.
    # Precisa caber um timeout do GPT Image e mais um retry (120s + folga + 120s).
    # Com 150s o primeiro timeout de 120s cancelava o retry e a figura sumia.
    preview_image_timeout_s: float = 260.0
    job_heartbeat_interval_s: float = 30.0
    # None = ligado só em prod. O worker free do Render dorme; a API acorda
    # com o polling da tela e precisa ela mesma tirar a prévia da fila.
    api_job_pump: bool | None = None
    ebook_pages: int = 6
    # Fichas turnaround/expressao/figurino antes das paginas (custo extra).
    ebook_character_bible: bool = False
    # True = refine de cena permitido. Quem dispara e o juiz de rosto
    # (`ebook_face_match`); false nunca refina (corte de custo).
    ebook_refine_scene: bool = False
    # Paginas ilustradas em paralelo (writes no banco ficam em serie, depois).
    ebook_page_concurrency: int = 3
    # Gemini/InsightFace comparam recorte/avatar x cena; abaixo do limiar roda
    # refine. Depois de 2 tentativas, score baixo/None recusa o job.
    ebook_face_match: bool = False
    ebook_face_match_min: float = 0.72
    # Avatar x cena (mesmo estilo). Acima do limiar foto x ilustracao, senao
    # um loiro generico passa. Abaixo disto: refine_scene OpenAI.
    ebook_avatar_match_min: float = 0.75
    avatar_face_match_min: float = 0.80
    # Close que infla o olho (fracao do rosto) acima disto recusa a pagina.
    ebook_eye_inflate_max: float = 0.15
    video_poll_interval_s: float = 10.0
    video_poll_timeout_s: float = 600.0

    # Comet Opik (tracing + avaliacao). Ligado se houver API key (Cloud) ou
    # URL override (self-host). Sem os dois, o wrapper e no-op.
    opik_api_key: str | None = None
    opik_workspace: str | None = None
    opik_project_name: str = "storyrus"
    opik_url_override: str | None = None
    opik_eval_story: bool = True

    def job_pump_enabled(self) -> bool:
        """Processa a fila dentro da API quando o worker separado está dormindo."""
        if self.api_job_pump is not None:
            return self.api_job_pump
        return self.app_env == "prod"

    def resolved_log_format(self) -> Literal["text", "json"]:
        """JSON em staging/prod por padrao; texto em dev (sobrescrevivel)."""
        if self.log_format == "auto":
            return "text" if self.app_env == "dev" else "json"
        return self.log_format

    @model_validator(mode="after")
    def _refuse_insecure_defaults_outside_dev(self) -> Self:
        """STO-8: staging/prod nao sobem com secrets `change-me-*`."""
        if self.app_env == "dev":
            return self
        bad: list[str] = []
        if _is_unsafe_secret(self.jwt_secret):
            bad.append("JWT_SECRET")
        if _is_unsafe_secret(self.webhook_signing_secret):
            bad.append("WEBHOOK_SIGNING_SECRET")
        # So recusa se o valor estiver explicitamente setado para default inseguro
        # (None/ausente e ok — storage pode ser local/offline).
        if self.storage_access_key is not None and _is_unsafe_secret(self.storage_access_key):
            bad.append("STORAGE_ACCESS_KEY")
        if self.storage_secret_key is not None and _is_unsafe_secret(self.storage_secret_key):
            bad.append("STORAGE_SECRET_KEY")
        if self.image_provider != "openai":
            bad.append("IMAGE_PROVIDER")
        if not (self.openai_api_key or "").strip():
            bad.append("OPENAI_API_KEY")
        if bad:
            raise ValueError(
                f"APP_ENV={self.app_env}: recusando secrets inseguros/default em "
                f"{', '.join(bad)}. Defina valores fortes via ambiente."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
