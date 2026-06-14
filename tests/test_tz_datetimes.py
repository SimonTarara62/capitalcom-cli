"""Datetimes must be timezone-aware (UTC) and emit no DeprecationWarning."""

import warnings
from datetime import datetime, timedelta, timezone

from capital_cli.core.models import PreviewResult, SessionTokens


def test_session_tokens_default_last_used_is_aware_utc():
    tokens = SessionTokens(cst="c", x_security_token="x")
    assert tokens.last_used_at.tzinfo is not None
    assert tokens.last_used_at.utcoffset() == timedelta(0)


def test_session_tokens_is_expired_with_aware_datetime():
    old = datetime.now(timezone.utc) - timedelta(minutes=10)
    tokens = SessionTokens(cst="c", x_security_token="x", last_used_at=old)
    assert tokens.is_expired() is True
    fresh = SessionTokens(
        cst="c", x_security_token="x", last_used_at=datetime.now(timezone.utc)
    )
    assert fresh.is_expired() is False


def test_preview_result_is_expired_with_aware_datetime():
    stale = PreviewResult(
        normalized_request={"epic": "GOLD"},
        checks=[],
        all_checks_passed=True,
        created_at=datetime.now(timezone.utc) - timedelta(seconds=600),
    )
    assert stale.is_expired() is True


def test_no_utcnow_deprecation_warning_in_risk_models_session():
    """Exercising the datetime paths must not emit a DeprecationWarning."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        # models: token + preview defaults
        tokens = SessionTokens(cst="c", x_security_token="x")
        tokens.update_last_used()
        tokens.is_expired()
        preview = PreviewResult(
            normalized_request={}, checks=[], all_checks_passed=True
        )
        preview.is_expired()
        # risk: daily-counter date key
        from capital_cli.core.risk import RiskEngine

        engine = RiskEngine()
        engine._check_daily_limit()
