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


def test_mutation_guard_blocks_in_dry_run():
    from capital_cli.core.config import get_config
    from capital_cli.core.errors import DryRunError

    cfg = get_config()
    cfg.cap_dry_run = True
    try:
        with pytest.raises(DryRunError):
            RiskEngine().validate_mutation_guards(confirm=True)
    finally:
        cfg.cap_dry_run = False


def test_mutation_guard_requires_confirm():
    from capital_cli.core.errors import ConfirmRequiredError

    with pytest.raises(ConfirmRequiredError):
        RiskEngine().validate_mutation_guards(confirm=False)


def test_mutation_guard_allows_without_trading_enabled():
    # Trading is disabled by default in the test config; a mutation must still be allowed.
    RiskEngine().validate_mutation_guards(confirm=True)  # must not raise


# ----- T6: enforce working-order size + max-open-positions limits -----


def _arm_market_details(engine, *, min_size=0.1, max_size=1000.0, increment=0.1):
    from unittest.mock import AsyncMock

    engine._get_market_details = AsyncMock(
        return_value={
            "dealingRules": {
                "minDealSize": {"value": min_size},
                "maxDealSize": {"value": max_size},
                "minSizeIncrement": {"value": increment},
            },
            "snapshot": {"bid": 2000.0, "offer": 2001.0},
        }
    )


async def test_working_order_size_uses_working_order_limit(monkeypatch):
    """A working order over cap_max_working_order_size fails, separate from cap_max_position_size."""
    from capital_cli.core.config import get_config
    from capital_cli.core.models import Direction, PreviewWorkingOrderRequest, WorkingOrderType

    cfg = get_config()
    cfg.cap_allow_trading = True
    cfg.cap_allowed_epics = "ALL"
    cfg.cap_max_position_size = 100.0
    cfg.cap_max_working_order_size = 1.0
    try:
        engine = RiskEngine()
        _arm_market_details(engine)
        request = PreviewWorkingOrderRequest(
            epic="GOLD",
            direction=Direction.BUY,
            type=WorkingOrderType.LIMIT,
            level=1900.0,
            size=5.0,  # within position limit (100) but over working-order limit (1)
        )
        result = await engine.preview_working_order(request)
        assert result.all_checks_passed is False
        failed = [c for c in result.checks if not c.passed]
        assert any(c.check == "max_working_order_size" for c in failed)
    finally:
        cfg.cap_allow_trading = False
        cfg.cap_allowed_epics = ""
        cfg.cap_max_position_size = 1.0
        cfg.cap_max_working_order_size = 1.0


def test_check_open_position_limit_rejects_at_cap():
    from capital_cli.core.config import get_config
    from capital_cli.core.errors import RiskLimitError

    cfg = get_config()
    cfg.cap_max_open_positions = 3
    try:
        engine = RiskEngine()
        engine.check_open_position_limit(2)  # below cap: ok
        with pytest.raises(RiskLimitError):
            engine.check_open_position_limit(3)  # at cap: reject
        with pytest.raises(RiskLimitError):
            engine.check_open_position_limit(5)  # over cap: reject
    finally:
        cfg.cap_max_open_positions = 3
