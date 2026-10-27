import pytest

from patchpilot.config import load_settings


def test_settings_loads_defaults_without_api_key(monkeypatch):
    for name in (
        "AI_PROVIDER", "GEMINI_MODEL", "GEMINI_API_KEY",
        "GEMINI_REQUEST_TIMEOUT_MS", "TEST_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = load_settings()

    assert settings.ai_provider == "gemini"
    assert settings.gemini_model == "gemini-3.8-flash"
    assert settings.gemini_api_key is None
    assert settings.gemini_request_timeout_ms == 90_000
    assert settings.test_timeout_seconds == 10


def test_settings_keep_model_configurable_and_validate_timeout(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "custom-model-name")
    monkeypatch.setenv("TEST_TIMEOUT_SECONDS", "0")

    with pytest.raises(ValueError, match="TEST_TIMEOUT_SECONDS"):
        load_settings()


def test_settings_uses_configured_gemini_request_timeout(monkeypatch):
    monkeypatch.setenv("GEMINI_REQUEST_TIMEOUT_MS", "90000")

    settings = load_settings()

    assert settings.gemini_request_timeout_ms == 90_000


def test_settings_load_configured_key_and_model_without_displaying_them(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-placeholder-secret")
    monkeypatch.setenv("GEMINI_MODEL", "test-only-model")

    settings = load_settings()

    assert settings.gemini_api_key == "test-only-placeholder-secret"
    assert settings.gemini_model == "test-only-model"
