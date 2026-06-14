"""Datetimes must be timezone-aware (UTC) and emit no DeprecationWarning."""

import warnings
from datetime import datetime, timedelta, timezone

from capital_cli.core.models import PreviewResult, SessionTokens, _as_utc


def test_as_utc_naive_datetime_becomes_aware_utc():
    """A naive datetime (legacy persisted) is treated as UTC: tzinfo is set to
    UTC while the wall-clock components stay unchanged."""
    naive = datetime(2024, 1, 2, 3, 4, 5)
    assert naive.tzinfo is None
    result = _as_utc(naive)
    assert result.tzinfo is not None
    assert result.utcoffset() == timedelta(0)
    assert result.replace(tzinfo=None) == naive


def test_as_utc_aware_datetime_passes_through_unchanged():
    aware = datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    result = _as_utc(aware)
    assert result == aware


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
