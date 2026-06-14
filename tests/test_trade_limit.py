"""Issue #2: --limit truncates positions/orders output."""

from capital_cli.services.trading import _apply_limit


def test_apply_limit_truncates():
    rows = [{"i": i} for i in range(10)]
    assert _apply_limit(rows, 3) == rows[:3]


def test_apply_limit_none_returns_all():
    rows = [{"i": i} for i in range(10)]
    assert _apply_limit(rows, None) == rows


def test_apply_limit_larger_than_len():
    rows = [{"i": 1}]
    assert _apply_limit(rows, 50) == rows
