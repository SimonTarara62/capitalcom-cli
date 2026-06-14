import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from capital_cli.cli.app import app
from capital_cli.cli.trade_cmds import _wait_for_confirmation


@pytest.fixture
def mock_trade(monkeypatch):
    sm = MagicMock()
    sm.ensure_logged_in = AsyncMock()
    sm.account_id = "ACC1"
    monkeypatch.setattr("capital_cli.cli.trade_cmds.get_session_manager", lambda: sm)

    client = MagicMock()
    resp = MagicMock()
    resp.json = MagicMock(
        return_value={
            "positions": [
                {
                    "position": {
                        "dealId": "D1",
                        "direction": "BUY",
                        "size": 1.0,
                        "level": 2000.0,
                        "upl": 5.0,
                    },
                    "market": {"epic": "GOLD", "instrumentName": "Gold"},
                }
            ]
        }
    )
    resp.text = "{}"
    client.get = AsyncMock(return_value=resp)
    client.post = AsyncMock(return_value=resp)
    client.delete = AsyncMock(return_value=resp)
    client.put = AsyncMock(return_value=resp)
    monkeypatch.setattr("capital_cli.cli.trade_cmds.get_client", lambda: client)

    # Risk engine: a passing preview.
    preview = MagicMock()
    preview.preview_id = "PV1"
    preview.normalized_request = {"epic": "GOLD", "direction": "BUY", "size": 1.0}
    preview.checks = [
        MagicMock(model_dump=lambda: {"check": "trading_enabled", "passed": True, "message": "ok"})
    ]
    preview.all_checks_passed = True
    preview.estimated_entry = 2001.0
    preview.estimated_risk_notes = "preview only"
    risk = MagicMock()
    risk.preview_position = AsyncMock(return_value=preview)
    risk.preview_working_order = AsyncMock(return_value=preview)
    monkeypatch.setattr("capital_cli.cli.trade_cmds.get_risk_engine", lambda: risk)
    return client


def test_positions_list(runner, mock_trade):
    result = runner.invoke(app, ["trade", "positions"])
    assert result.exit_code == 0
    assert "GOLD" in result.stdout


def test_orders_list_json(runner, mock_trade):
    result = runner.invoke(app, ["--json", "trade", "orders"])
    assert result.exit_code == 0
    assert mock_trade.get.await_args.args[0] == "/workingorders"


def test_confirm_get(runner, mock_trade):
    result = runner.invoke(app, ["trade", "confirm", "o_ref123"])
    assert result.exit_code == 0
    assert mock_trade.get.await_args.args[0] == "/confirms/o_ref123"


def test_preview_position(runner, mock_trade):
    result = runner.invoke(app, ["--json", "trade", "preview-position", "GOLD", "BUY", "1.0"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["preview_id"] == "PV1"


def _arm_execution(monkeypatch):
    """Make the risk engine permit execution and return the patched risk mock."""
    risk = MagicMock()
    preview = MagicMock()
    preview.normalized_request = {"epic": "GOLD", "direction": "BUY", "size": 1.0}
    risk.validate_execution_guards = MagicMock(return_value=None)
    risk.get_preview = MagicMock(return_value=preview)
    risk.increment_order_count = MagicMock()
    monkeypatch.setattr("capital_cli.cli.trade_cmds.get_risk_engine", lambda: risk)
    return risk


def test_execute_position_blocked_without_yes(runner, mock_trade, monkeypatch):
    risk = _arm_execution(monkeypatch)
    # Simulate guard raising when confirm is False.
    from capital_cli.core.errors import ConfirmRequiredError

    def guard(confirm, preview_id=None):
        if not confirm:
            raise ConfirmRequiredError()

    risk.validate_execution_guards = MagicMock(side_effect=guard)
    result = runner.invoke(app, ["trade", "execute-position", "PV1"])
    assert result.exit_code == 4
    mock_trade.post.assert_not_awaited()


def test_execute_position_with_yes(runner, mock_trade, monkeypatch):
    _arm_execution(monkeypatch)
    mock_trade.post.return_value.json.return_value = {"dealReference": "o_x"}
    result = runner.invoke(
        app, ["--json", "trade", "execute-position", "PV1", "--yes", "--no-wait"]
    )
    assert result.exit_code == 0
    assert mock_trade.post.await_args.args[0] == "/positions"
    assert mock_trade.post.await_args.kwargs["rate_limit_type"] == "trading"


def test_execute_position_rejected_at_open_position_limit(runner, mock_trade, monkeypatch):
    from capital_cli.core.errors import RiskLimitError

    risk = _arm_execution(monkeypatch)

    def limit(count):
        raise RiskLimitError("Open position limit reached (3)")

    risk.check_open_position_limit = MagicMock(side_effect=limit)
    # /positions returns one open position (count source).
    mock_trade.get.return_value.json.return_value = {"positions": [{"position": {}}]}
    result = runner.invoke(app, ["trade", "execute-position", "PV1", "--yes", "--no-wait"])
    assert result.exit_code == 4  # RISK_LIMIT
    mock_trade.post.assert_not_awaited()


def test_close_position_with_yes(runner, mock_trade, monkeypatch):
    _arm_execution(monkeypatch)
    mock_trade.delete.return_value.json.return_value = {"dealReference": "o_c"}
    result = runner.invoke(app, ["trade", "close", "D1", "--yes", "--no-wait"])
    assert result.exit_code == 0
    assert mock_trade.delete.await_args.args[0] == "/positions/D1"


# ----- _wait_for_confirmation: dealStatus vs status normalization -----


def _client_returning(monkeypatch, *json_payloads):
    """Patch get_client() to return a client whose GET yields the given JSON
    payloads in order (last payload repeats if more calls happen)."""
    client = MagicMock()
    resp = MagicMock()
    resp.json = MagicMock(side_effect=list(json_payloads) + [json_payloads[-1]] * 10)
    client.get = AsyncMock(return_value=resp)
    monkeypatch.setattr("capital_cli.cli.trade_cmds.get_client", lambda: client)
    return client


async def test_wait_for_confirmation_accepted_normalizes_status(monkeypatch):
    _client_returning(
        monkeypatch,
        {
            "dealStatus": "ACCEPTED",
            "status": "OPEN",
            "dealId": "D1",
            "affectedDeals": [{"dealId": "D1", "status": "OPENED"}],
        },
    )

    result = await _wait_for_confirmation("o_ref1", timeout_s=5.0)

    # status is normalized from dealStatus, overriding the lifecycle "OPEN" value.
    assert result["status"] == "ACCEPTED"
    assert result["dealStatus"] == "ACCEPTED"
    assert result["dealId"] == "D1"
    assert result["affectedDeals"] == [{"dealId": "D1", "status": "OPENED"}]


async def test_wait_for_confirmation_rejected_preserves_reason(monkeypatch):
    _client_returning(
        monkeypatch,
        {
            "dealStatus": "REJECTED",
            "status": "REJECTED",
            "dealId": "D2",
            "reason": "RISK_CHECK_FAILED",
        },
    )

    result = await _wait_for_confirmation("o_ref2", timeout_s=5.0)

    assert result["status"] == "REJECTED"
    assert result["dealStatus"] == "REJECTED"
    assert result["reason"] == "RISK_CHECK_FAILED"


async def test_wait_for_confirmation_polls_past_pending(monkeypatch):
    client = _client_returning(
        monkeypatch,
        {"dealStatus": "PENDING", "status": "OPEN"},
        {"dealStatus": "ACCEPTED", "status": "OPEN", "dealId": "D3"},
    )

    result = await _wait_for_confirmation("o_ref3", timeout_s=5.0, poll_interval_ms=100)

    assert result["status"] == "ACCEPTED"
    assert client.get.await_count >= 2


async def test_wait_for_confirmation_surfaces_broker_error(monkeypatch):
    """A non-transient broker error during polling must surface, not become TIMEOUT."""
    from capital_cli.core.errors import UpstreamError

    client = MagicMock()
    client.get = AsyncMock(side_effect=UpstreamError("not found", status_code=404))
    monkeypatch.setattr("capital_cli.cli.trade_cmds.get_client", lambda: client)

    with pytest.raises(UpstreamError):
        await _wait_for_confirmation("o_bad", timeout_s=2.0, poll_interval_ms=100)


async def test_wait_for_confirmation_timeout(monkeypatch):
    _client_returning(monkeypatch, {"dealStatus": "PENDING", "status": "OPEN"})

    result = await _wait_for_confirmation("o_ref4", timeout_s=0.5, poll_interval_ms=100)

    assert result["status"] == "TIMEOUT"
    assert "message" in result


def test_amend_position_blocked_without_yes(runner, mock_trade, monkeypatch):
    risk = _arm_execution(monkeypatch)
    from capital_cli.core.errors import ConfirmRequiredError

    def guard(confirm, preview_id=None):
        if not confirm:
            raise ConfirmRequiredError()

    risk.validate_execution_guards = MagicMock(side_effect=guard)
    result = runner.invoke(app, ["trade", "amend-position", "D1", "--stop-level", "100"])
    assert result.exit_code == 4
    mock_trade.put.assert_not_awaited()


def test_amend_position_no_fields_is_usage_error(runner, mock_trade, monkeypatch):
    _arm_execution(monkeypatch)
    result = runner.invoke(app, ["trade", "amend-position", "D1", "--yes"])
    assert result.exit_code == 2  # nothing to amend -> BadParameter
    mock_trade.put.assert_not_awaited()


def test_amend_position_with_yes(runner, mock_trade, monkeypatch):
    _arm_execution(monkeypatch)
    mock_trade.put.return_value.json.return_value = {"dealReference": "o_a"}
    result = runner.invoke(
        app,
        [
            "trade",
            "amend-position",
            "D1",
            "--stop-level",
            "100",
            "--profit-level",
            "200",
            "--yes",
            "--no-wait",
        ],
    )
    assert result.exit_code == 0
    assert mock_trade.put.await_args.args[0] == "/positions/D1"
    assert mock_trade.put.await_args.kwargs["json"] == {"stopLevel": 100.0, "profitLevel": 200.0}


def test_amend_order_with_yes(runner, mock_trade, monkeypatch):
    _arm_execution(monkeypatch)
    mock_trade.put.return_value.json.return_value = {"dealReference": "o_b"}
    result = runner.invoke(
        app,
        [
            "trade",
            "amend-order",
            "D2",
            "--level",
            "2300",
            "--good-till",
            "2026-07-01T00:00:00",
            "--yes",
            "--no-wait",
        ],
    )
    assert result.exit_code == 0
    assert mock_trade.put.await_args.args[0] == "/workingorders/D2"
    assert mock_trade.put.await_args.kwargs["json"] == {
        "level": 2300.0,
        "goodTillDate": "2026-07-01T00:00:00",
    }


def test_amend_order_no_fields_is_usage_error(runner, mock_trade, monkeypatch):
    _arm_execution(monkeypatch)
    result = runner.invoke(app, ["trade", "amend-order", "D2", "--yes"])
    assert result.exit_code == 2
    mock_trade.put.assert_not_awaited()


def test_preview_position_passes_auto_normalize_flag(runner, monkeypatch):
    from unittest.mock import AsyncMock, MagicMock

    sm = MagicMock()
    sm.ensure_logged_in = AsyncMock()
    monkeypatch.setattr("capital_cli.cli.trade_cmds.get_session_manager", lambda: sm)
    preview = MagicMock()
    preview.preview_id = "PV1"
    preview.normalized_request = {"epic": "GOLD"}
    preview.checks = []
    preview.all_checks_passed = True
    preview.estimated_entry = 1.0
    preview.estimated_risk_notes = "x"
    risk = MagicMock()
    risk.preview_position = AsyncMock(return_value=preview)
    monkeypatch.setattr("capital_cli.cli.trade_cmds.get_risk_engine", lambda: risk)

    result = runner.invoke(
        app, ["--json", "trade", "preview-position", "GOLD", "BUY", "0.5", "--auto-normalize-size"]
    )
    assert result.exit_code == 0
    assert risk.preview_position.await_args.args[0].auto_normalize_size is True
