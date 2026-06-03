import logging
from unittest.mock import patch

import pytest

from src.config import Settings


def make_settings(**overrides) -> Settings:
    defaults = dict(
        DATABASE_URL="postgresql+asyncpg://localhost/test",
        SUPABASE_URL="http://localhost",
        SUPABASE_ANON_KEY="test-key",
        CORS_ORIGINS="http://localhost:3000",
        APP_ENV="development",
        CURRENT_TERM="202690",
        SENTRY_DSN="",
    )
    defaults.update(overrides)
    return Settings(**defaults)


def test_missing_database_url_exits_in_production():
    s = make_settings(DATABASE_URL="", APP_ENV="production")
    with patch("sys.exit") as mock_exit:
        s.validate_for_production()
    mock_exit.assert_called_with(1)


def test_missing_vars_only_warn_in_development(caplog):
    s = make_settings(DATABASE_URL="")
    with caplog.at_level(logging.WARNING, logger="src.config"):
        s.validate_for_production()
    assert "DATABASE_URL" in caplog.text


def test_change_me_value_treated_as_missing():
    s = make_settings(DATABASE_URL="CHANGE_ME", APP_ENV="production")
    with patch("sys.exit") as mock_exit:
        s.validate_for_production()
    mock_exit.assert_called_with(1)


def test_sentry_dsn_warning_when_empty(caplog):
    s = make_settings(SENTRY_DSN="")
    with caplog.at_level(logging.WARNING, logger="src.config"):
        s.validate_for_production()
    assert "SENTRY_DSN" in caplog.text


def test_no_warnings_when_all_vars_set_with_sentry(caplog):
    s = make_settings(SENTRY_DSN="https://xxx@sentry.io/123")
    with caplog.at_level(logging.WARNING, logger="src.config"):
        s.validate_for_production()
    assert "FATAL" not in caplog.text
    assert "SENTRY_DSN" not in caplog.text
