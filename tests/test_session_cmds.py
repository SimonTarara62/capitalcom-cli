import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from capital_cli.cli.app import app


def test_status_json(runner, mock_session):
    result = runner.invoke(app, ["--json", "session", "status"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["account_id"] == "ACC1"


def test_status_table(runner, mock_session):
    result = runner.invoke(app, ["session", "status"])
    assert result.exit_code == 0
    assert "ACC1" in result.stdout


def test_login_calls_core(runner, mock_session):
    result = runner.invoke(app, ["session", "login", "--force"])
    assert result.exit_code == 0
    mock_session.login.assert_awaited_once()
    assert mock_session.login.await_args.kwargs["force"] is True


def test_ping(runner, mock_session):
    result = runner.invoke(app, ["--json", "session", "ping"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["status"] == "OK"


def test_logout(runner, mock_session):
    result = runner.invoke(app, ["session", "logout"])
    assert result.exit_code == 0
    mock_session.logout.assert_awaited_once()


def test_switch(runner, mock_session):
    result = runner.invoke(app, ["session", "switch", "ACC2"])
    assert result.exit_code == 0
    mock_session.switch_account.assert_awaited_once_with("ACC2")


@pytest.fixture
def mock_session_client(monkeypatch):
    """Patch the SessionManager read methods backing the session commands.

    The CLI now delegates to ``get_session_manager().server_time()`` etc. rather
    than calling the HTTP client inline, so we stub those passthroughs.
    """
    sm = MagicMock()
    sm.ensure_logged_in = AsyncMock()
    sm.server_time = AsyncMock(return_value={})
    sm.details = AsyncMock(return_value={})
    sm.encryption_key = AsyncMock(return_value={})
    monkeypatch.setattr("capital_cli.cli.session_cmds.get_session_manager", lambda: sm)
    return sm


def test_time(runner, mock_session_client):
    mock_session_client.server_time.return_value = {"serverTime": 1700000000000}
    result = runner.invoke(app, ["--json", "session", "time"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["serverTime"] == 1700000000000
    mock_session_client.server_time.assert_awaited_once()


def test_details(runner, mock_session_client):
    mock_session_client.details.return_value = {"clientId": "C1", "accountId": "A1"}
    result = runner.invoke(app, ["--json", "session", "details"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["clientId"] == "C1"
    mock_session_client.details.assert_awaited_once()


def test_encryption_key(runner, mock_session_client):
    mock_session_client.encryption_key.return_value = {"encryptionKey": "K", "timeStamp": 1}
    result = runner.invoke(app, ["session", "encryption-key"])
    assert result.exit_code == 0
    mock_session_client.encryption_key.assert_awaited_once()
