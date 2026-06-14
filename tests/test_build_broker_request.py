"""Regression test for issue #8: numeric stop/profit fields equal to 0.0 must
not be dropped by truthiness checks when building the broker request body."""

from capital_cli.cli.trade_cmds import _build_broker_request


def test_zero_valued_stop_and_profit_fields_are_kept():
    normalized = {
        "epic": "GOLD",
        "direction": "BUY",
        "size": 1.0,
        "stop_level": 0.0,
        "stop_distance": 0.0,
        "profit_level": 0.0,
        "profit_distance": 0.0,
    }
    body = _build_broker_request(normalized, include_order_fields=False)
    assert body["stopLevel"] == 0.0
    assert body["stopDistance"] == 0.0
    assert body["profitLevel"] == 0.0
    assert body["profitDistance"] == 0.0


def test_absent_fields_are_omitted():
    normalized = {"epic": "GOLD", "direction": "BUY", "size": 1.0}
    body = _build_broker_request(normalized, include_order_fields=False)
    assert "stopLevel" not in body
    assert "profitDistance" not in body
    assert body == {"epic": "GOLD", "direction": "BUY", "size": 1.0}
