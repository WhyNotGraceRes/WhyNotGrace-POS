"""Unit tests for Settings.validate_production_safety — no DB/client needed,
these exercise the Settings class directly.
"""
import pytest

from app.core.config import Settings


def _valid_production_kwargs(**overrides):
    kwargs = dict(
        app_env="production",
        debug=False,
        jwt_secret="a" * 64,
        email_backend="smtp",
        smtp_host="smtp.example.com",
        postgres_password="a-real-production-password",
        razorpay_key_id="rzp_live_x",
        razorpay_key_secret="live-secret",
        cors_origins="https://app.example.com",
        # Must be declared explicitly in production: an undeclared reverse
        # proxy makes every request carry the proxy's own IP, which turns
        # each per-client rate limit into one global limit for the entire
        # deployment. See app/core/client_ip.py.
        trusted_proxy_ips="*",
    )
    kwargs.update(overrides)
    return kwargs


def test_valid_production_config_passes():
    settings = Settings(**_valid_production_kwargs())
    settings.validate_production_safety()  # must not raise


def test_wildcard_cors_rejected_in_production():
    settings = Settings(**_valid_production_kwargs(cors_origins="*"))
    with pytest.raises(RuntimeError, match="CORS_ORIGINS must not be"):
        settings.validate_production_safety()


def test_wildcard_among_multiple_origins_still_rejected():
    settings = Settings(**_valid_production_kwargs(cors_origins="https://app.example.com,*"))
    with pytest.raises(RuntimeError, match="CORS_ORIGINS must not be"):
        settings.validate_production_safety()


def test_development_config_never_raises_even_with_wildcard_cors():
    settings = Settings(app_env="development", cors_origins="*")
    settings.validate_production_safety()  # must not raise — only enforced in production


def test_insecure_jwt_secret_still_rejected_in_production():
    settings = Settings(**_valid_production_kwargs(jwt_secret="dev-only-insecure-secret-change-me"))
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        settings.validate_production_safety()
