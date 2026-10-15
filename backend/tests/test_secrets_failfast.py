"""STO-8: secrets fail-fast quando APP_ENV != dev."""

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_production_defaults_to_real_openai_generation(monkeypatch):
    monkeypatch.delenv("OFFLINE_FALLBACK", raising=False)
    settings = Settings(
        _env_file=None,
        app_env="prod",
        jwt_secret="strong-jwt-secret-value",
        webhook_signing_secret="strong-webhook-secret-value",
        openai_api_key="test-openai-key",
    )
    assert settings.offline_fallback is False
    assert settings.image_provider == "openai"


def test_dev_allows_default_secrets():
    s = Settings(
        app_env="dev",
        jwt_secret="change-me-in-prod",
        webhook_signing_secret="change-me-webhook",
    )
    assert s.app_env == "dev"


@pytest.mark.parametrize("env", ["staging", "prod"])
def test_non_dev_rejects_default_jwt(env):
    with pytest.raises(ValidationError) as exc:
        Settings(
            app_env=env,
            jwt_secret="change-me-in-prod",
            webhook_signing_secret="a-strong-webhook-secret-value",
        )
    assert "JWT_SECRET" in str(exc.value)


@pytest.mark.parametrize("env", ["staging", "prod"])
def test_non_dev_rejects_default_webhook(env):
    with pytest.raises(ValidationError) as exc:
        Settings(
            app_env=env,
            jwt_secret="a-strong-jwt-secret-value",
            webhook_signing_secret="change-me-webhook",
        )
    assert "WEBHOOK_SIGNING_SECRET" in str(exc.value)


@pytest.mark.parametrize("env", ["staging", "prod"])
def test_non_dev_rejects_unsafe_storage_keys(env):
    with pytest.raises(ValidationError) as exc:
        Settings(
            app_env=env,
            jwt_secret="a-strong-jwt-secret-value",
            webhook_signing_secret="a-strong-webhook-secret-value",
            storage_access_key="change-me",
            storage_secret_key="ok-secret",
        )
    assert "STORAGE_ACCESS_KEY" in str(exc.value)


@pytest.mark.parametrize("env", ["staging", "prod"])
def test_non_dev_accepts_strong_secrets(env):
    s = Settings(
        app_env=env,
        jwt_secret="a-strong-jwt-secret-value",
        webhook_signing_secret="a-strong-webhook-secret-value",
        storage_access_key=None,
        storage_secret_key=None,
        openai_api_key="sk-openai-test-key",
    )
    assert s.app_env == env


@pytest.mark.parametrize("env", ["staging", "prod"])
def test_non_dev_openai_provider_requires_api_key(env):
    with pytest.raises(ValidationError) as exc:
        Settings(
            app_env=env,
            jwt_secret="a-strong-jwt-secret-value",
            webhook_signing_secret="a-strong-webhook-secret-value",
            image_provider="openai",
            openai_api_key="",
        )
    assert "OPENAI_API_KEY" in str(exc.value)


@pytest.mark.parametrize("env", ["staging", "prod"])
def test_non_dev_rejects_non_openai_image_provider(env):
    with pytest.raises(ValidationError) as exc:
        Settings(
            app_env=env,
            jwt_secret="a-strong-jwt-secret-value",
            webhook_signing_secret="a-strong-webhook-secret-value",
            image_provider="nano-banana",
            openai_api_key="sk-openai-test-key",
        )
    assert "IMAGE_PROVIDER" in str(exc.value)
