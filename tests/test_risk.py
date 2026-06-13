"""Unit tests for RiskEngine size validation and guard flows (offline)."""

import pytest

from capital_cli.core.models import RiskCheck
from capital_cli.core.risk import RiskEngine


def _validate(size, *, min_size=0.01, max_size=100.0, increment=0.01, auto=False):
    engine = RiskEngine()
    return engine._validate_size(size, min_size, max_size, increment, auto_normalize=auto)


def test_size_below_minimum_fails_and_is_unchanged():
    effective, check = _validate(0.001, min_size=0.01)
    assert isinstance(check, RiskCheck)
    assert check.passed is False
    assert effective == 0.001
    assert "below" in check.message.lower()


def test_size_above_maximum_fails_and_is_unchanged():
    effective, check = _validate(500.0, max_size=100.0)
    assert check.passed is False
    assert effective == 500.0
    assert "above" in check.message.lower()


def test_aligned_size_passes_unchanged():
    effective, check = _validate(0.05, increment=0.01)
    assert check.passed is True
    assert effective == 0.05


def test_misaligned_size_fails_without_opt_in():
    effective, check = _validate(0.055, increment=0.01, auto=False)
    assert check.passed is False
    assert effective == 0.055
    assert "--auto-normalize-size" in check.message


def test_misaligned_size_rounds_only_with_opt_in():
    effective, check = _validate(0.054, increment=0.01, auto=True)
    assert check.passed is True
    assert effective == pytest.approx(0.05)
    assert "normalized" in check.message.lower()


def test_auto_normalize_still_fails_if_rounding_crosses_minimum():
    # 0.0124 is >= the 0.012 minimum, but rounding to the 0.01 increment gives
    # 0.01, which is below the minimum -> must fail even with the opt-in, and the
    # size must be returned unchanged.
    effective, check = _validate(0.0124, min_size=0.012, max_size=100.0, increment=0.01, auto=True)
    assert check.passed is False
    assert effective == 0.0124
    assert "0.01" in check.message  # mentions the out-of-range rounded value
