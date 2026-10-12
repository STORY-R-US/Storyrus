"""A API em prod consome a fila quando o worker free está dormindo."""

from app.config import Settings


def test_job_pump_ligado_em_prod_e_desligado_em_dev():
    dev = Settings(app_env="dev")
    prod = Settings(
        app_env="prod",
        jwt_secret="a-real-prod-secret-value",
        webhook_signing_secret="another-real-prod-secret",
        openai_api_key="sk-test",
    )
    assert dev.job_pump_enabled() is False
    assert prod.job_pump_enabled() is True


def test_kick_acorda_o_pump():
    from app.workers import api_pump

    api_pump._wake.clear()
    api_pump.kick()
    assert api_pump._wake.is_set()


def test_preview_image_timeout_covers_one_openai_retry():
    """O teto da figura não pode ser menor que um timeout do GPT Image mais um retry."""
    dev = Settings()
    assert dev.preview_image_timeout_s >= dev.openai_timeout_s * 2 + dev.openai_retry_base_s


def test_job_pump_respeita_override():
    forced_off = Settings(
        app_env="prod",
        api_job_pump=False,
        jwt_secret="a-real-prod-secret-value",
        webhook_signing_secret="another-real-prod-secret",
        openai_api_key="sk-test",
    )
    forced_on = Settings(app_env="dev", api_job_pump=True)
    assert forced_off.job_pump_enabled() is False
    assert forced_on.job_pump_enabled() is True
