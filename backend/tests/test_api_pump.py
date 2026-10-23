"""A API em prod consome a fila quando o worker free está dormindo."""

from app.config import Settings


def test_job_pump_ligado_em_prod_e_desligado_em_dev():
    dev = Settings(app_env="dev")
    prod = Settings(
        app_env="prod",
        jwt_secret="a-real-prod-secret-value",
        webhook_signing_secret="another-real-prod-secret",
        openai_api_key="sk-test",
        clerk_secret_key="sk_test_clerk_secret_value",
        storage_access_key=None,
        storage_secret_key=None,
    )
    assert dev.job_pump_enabled() is False
    assert prod.job_pump_enabled() is True


def test_kick_acorda_o_pump():
    from app.workers import api_pump

    api_pump._wake.clear()
    api_pump.kick()
    assert api_pump._wake.is_set()


def test_preview_image_timeout_covers_one_openai_attempt():
    """O teto da figura precisa cobrir um disparo do GPT Image (com folga).

    A prévia é best-effort: com as três figuras em paralelo, esperar um retry
    inteiro deixava o passo em Imagens por muitos minutos. O teto cobre um
    disparo para não cortar um sucesso lento no meio.
    """
    dev = Settings()
    assert dev.preview_image_timeout_s >= dev.openai_timeout_s + dev.openai_retry_base_s


def test_job_pump_respeita_override():
    forced_off = Settings(
        app_env="prod",
        api_job_pump=False,
        jwt_secret="a-real-prod-secret-value",
        webhook_signing_secret="another-real-prod-secret",
        openai_api_key="sk-test",
        clerk_secret_key="sk_test_clerk_secret_value",
        storage_access_key=None,
        storage_secret_key=None,
    )
    forced_on = Settings(app_env="dev", api_job_pump=True)
    assert forced_off.job_pump_enabled() is False
    assert forced_on.job_pump_enabled() is True
