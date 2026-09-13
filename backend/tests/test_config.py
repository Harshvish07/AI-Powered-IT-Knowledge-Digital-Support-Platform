"""Unit tests for the production-safety startup guard (app/core/config.py).
Pure config-object tests — no HTTP client, no database — since
assert_production_safe() is a plain function of a Settings instance.
"""

import pytest

from app.core.config import Settings, assert_production_safe


def _base_production_settings(**overrides: object) -> Settings:
    """A Settings instance representing a *correctly configured* production
    deployment — every test below overrides exactly one field to break it."""
    defaults: dict[str, object] = {
        "environment": "production",
        "jwt_secret_key": "a-real-randomly-generated-secret-not-the-dev-default",
        "debug": False,
        "cookie_secure": True,
        "cors_origins": ["https://app.example.com"],
        "gemini_api_key": "real-key",
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


def test_development_environment_is_never_blocked() -> None:
    # Every field below is individually "unsafe for production", but since
    # environment is development, assert_production_safe must be a no-op.
    settings = Settings(
        environment="development",
        jwt_secret_key="dev-insecure-secret-change-me-before-deploying-anywhere",
        debug=True,
        cookie_secure=False,
        cors_origins=["http://localhost:3000"],
        gemini_api_key=None,
    )
    assert_production_safe(settings)  # must not raise


def test_correctly_configured_production_settings_pass() -> None:
    assert_production_safe(_base_production_settings())  # must not raise


def test_production_rejects_dev_default_jwt_secret() -> None:
    settings = _base_production_settings(
        jwt_secret_key="dev-insecure-secret-change-me-before-deploying-anywhere"
    )
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        assert_production_safe(settings)


def test_production_rejects_debug_true() -> None:
    settings = _base_production_settings(debug=True)
    with pytest.raises(RuntimeError, match="DEBUG"):
        assert_production_safe(settings)


def test_production_rejects_insecure_cookie() -> None:
    settings = _base_production_settings(cookie_secure=False)
    with pytest.raises(RuntimeError, match="COOKIE_SECURE"):
        assert_production_safe(settings)


def test_production_rejects_localhost_cors_origin() -> None:
    settings = _base_production_settings(cors_origins=["http://localhost:3000"])
    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        assert_production_safe(settings)


def test_production_rejects_missing_gemini_key() -> None:
    settings = _base_production_settings(gemini_api_key=None)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        assert_production_safe(settings)


def test_production_reports_every_problem_at_once() -> None:
    settings = _base_production_settings(
        jwt_secret_key="dev-insecure-secret-change-me-before-deploying-anywhere",
        debug=True,
        cookie_secure=False,
    )
    with pytest.raises(RuntimeError) as exc_info:
        assert_production_safe(settings)
    message = str(exc_info.value)
    assert "JWT_SECRET_KEY" in message
    assert "DEBUG" in message
    assert "COOKIE_SECURE" in message
