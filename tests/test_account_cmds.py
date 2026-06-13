import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from capital_cli.cli.app import app


@pytest.fixture
def mock_account(monkeypatch):
    sm = MagicMock()
    sm.ensure_logged_in = AsyncMock()
    sm.account_id = "ACC1"
    monkeypatch.setattr("capital_cli.cli.account_cmds.get_session_manager", lambda: sm)

    client = MagicMock()
    resp = MagicMock()
    resp.json = MagicMock(
        return_value={
            "accounts": [
                {
                    "accountId": "ACC1",
                    "accountName": "Demo",
                    "balance": {"balance": 1000.0},
                    "currency": "USD",
                }
            ]
        }
    )
    client.get = AsyncMock(return_value=resp)
    client.put = AsyncMock(return_value=resp)
    client.post = AsyncMock(return_value=resp)
    monkeypatch.setattr("capital_cli.cli.account_cmds.get_client", lambda: client)
    return client


def test_list(runner, mock_account):
    result = runner.invoke(app, ["account", "list"])
    assert result.exit_code == 0
    assert "ACC1" in result.stdout


def test_list_json(runner, mock_account):
    result = runner.invoke(app, ["--json", "account", "list"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["accounts"][0]["accountId"] == "ACC1"


def test_demo_topup_requires_confirm(runner, mock_account):
    # Default config has require_explicit_confirm=true; no --yes => blocked.
    result = runner.invoke(app, ["account", "topup", "500"])
    assert result.exit_code == 4  # CONFIRM_REQUIRED
    mock_account.post.assert_not_awaited()


def test_demo_topup_with_yes(runner, mock_account):
    result = runner.invoke(app, ["account", "topup", "500", "--yes"])
    assert result.exit_code == 0
    assert mock_account.post.await_args.args[0] == "/accounts/topUp"
    assert mock_account.post.await_args.kwargs["json"] == {"amount": 500.0}


def test_history_activity_detailed(runner, mock_account):
    mock_account.get.return_value.json.return_value = {"activities": []}
    result = runner.invoke(
        app,
        ["--json", "account", "history-activity", "--last", "3600", "--detailed", "--deal-id", "D9"],
    )
    assert result.exit_code == 0
    params = mock_account.get.await_args.kwargs["params"]
    assert params["detailed"] == "true"
    assert params["dealId"] == "D9"
    assert params["lastPeriod"] == 3600


def _arm_prefs(monkeypatch):
    """Make the risk engine permit the risk-gated prefs-set."""
    from unittest.mock import MagicMock

    risk = MagicMock()
    risk.validate_execution_guards = MagicMock(return_value=None)
    monkeypatch.setattr("capital_cli.cli.account_cmds.get_risk_engine", lambda: risk)
    return risk


def test_prefs_set_leverage(runner, mock_account, monkeypatch):
    _arm_prefs(monkeypatch)
    mock_account.put.return_value.json.return_value = {"status": "SUCCESS"}
    result = runner.invoke(
        app,
        ["account", "prefs-set", "--leverage", "CRYPTOCURRENCIES=2", "--leverage", "CURRENCIES=20", "--yes"],
    )
    assert result.exit_code == 0
    assert mock_account.put.await_args.args[0] == "/accounts/preferences"
    assert mock_account.put.await_args.kwargs["json"] == {
        "leverages": {"CRYPTOCURRENCIES": 2, "CURRENCIES": 20}
    }


def test_prefs_set_hedging_and_leverage(runner, mock_account, monkeypatch):
    _arm_prefs(monkeypatch)
    mock_account.put.return_value.json.return_value = {"status": "SUCCESS"}
    result = runner.invoke(
        app, ["account", "prefs-set", "--no-hedging", "--leverage", "SHARES=5", "--yes"]
    )
    assert result.exit_code == 0
    assert mock_account.put.await_args.kwargs["json"] == {
        "hedgingMode": False,
        "leverages": {"SHARES": 5},
    }


def test_prefs_set_requires_some_field(runner, mock_account, monkeypatch):
    _arm_prefs(monkeypatch)
    result = runner.invoke(app, ["account", "prefs-set", "--yes"])
    assert result.exit_code == 2  # nothing to set -> BadParameter
    mock_account.put.assert_not_awaited()


def test_prefs_set_bad_leverage_format(runner, mock_account, monkeypatch):
    _arm_prefs(monkeypatch)
    result = runner.invoke(app, ["account", "prefs-set", "--leverage", "CRYPTO", "--yes"])
    assert result.exit_code == 2
    mock_account.put.assert_not_awaited()


def test_prefs_set_leverage_works_without_trading_enabled(runner, mock_account):
    # No risk-engine patching: with the REAL guards and trading disabled, prefs-set
    # must NOT require CAP_ALLOW_TRADING — only --yes.
    mock_account.put.return_value.json.return_value = {"status": "SUCCESS"}
    result = runner.invoke(app, ["account", "prefs-set", "--leverage", "SHARES=5", "--yes"])
    assert result.exit_code == 0
    assert mock_account.put.await_args.kwargs["json"] == {"leverages": {"SHARES": 5}}


def test_prefs_set_still_requires_confirm(runner, mock_account):
    result = runner.invoke(app, ["account", "prefs-set", "--leverage", "SHARES=5"])
    assert result.exit_code == 4  # CONFIRM_REQUIRED
    mock_account.put.assert_not_awaited()
