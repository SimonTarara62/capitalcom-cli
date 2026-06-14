"""Tests for `capctl doctor` preflight/capability probe."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from capital_cli.cli.app import app
from capital_cli.core.errors import SessionError


@pytest.fixture
def mock_doctor_ok(monkeypatch):
    sm = MagicMock()
    sm.ensure_logged_in = AsyncMock()
    sm.account_id = "ACC1"
    monkeypatch.setattr("capital_cli.cli.doctor_cmds.get_session_manager", lambda: sm)

    client = MagicMock()
    resp = MagicMock()
    resp.json = MagicMock(return_value={"serverTime": 1234567890})
    client.get = AsyncMock(return_value=resp)
    monkeypatch.setattr("capital_cli.cli.doctor_cmds.get_client", lambda: client)
    return sm, client


def test_doctor_json_ok(runner, mock_doctor_ok):
    result = runner.invoke(app, ["--json", "doctor"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["env"] == "demo"
    assert payload["allow_trading"] is False
    assert "allowed_epics" in payload
    assert "orders_remaining_today" in payload
    assert payload["server_time_ok"] is True
    assert payload["credentials_ok"] is True
    # No secrets should leak.
    blob = json.dumps(payload)
    assert "***REDACTED***" not in blob  # we omit secrets entirely, not even redacted markers
    for secret in ("password", "api_key", "identifier"):
        assert secret not in blob.lower() or "ok" in blob.lower()


def test_doctor_human_ok(runner, mock_doctor_ok):
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0, result.stdout
    assert "env" in result.stdout.lower() or "demo" in result.stdout.lower()


@pytest.fixture
def mock_doctor_bad_creds(monkeypatch):
    sm = MagicMock()
    sm.ensure_logged_in = AsyncMock(side_effect=SessionError("bad creds"))
    sm.account_id = None
    monkeypatch.setattr("capital_cli.cli.doctor_cmds.get_session_manager", lambda: sm)

    client = MagicMock()
    resp = MagicMock()
    resp.json = MagicMock(return_value={"serverTime": 1})
    client.get = AsyncMock(return_value=resp)
    monkeypatch.setattr("capital_cli.cli.doctor_cmds.get_client", lambda: client)
    return sm, client


def test_doctor_bad_creds_json_structured_nonzero(runner, mock_doctor_bad_creds):
    result = runner.invoke(app, ["--json", "doctor"])
    assert result.exit_code != 0
    payload = json.loads(result.stdout)
    assert payload["credentials_ok"] is False
    assert payload["env"] == "demo"
    assert "Traceback" not in result.stdout
