"""Tests for `capctl doctor` preflight/capability probe."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from capital_cli.cli.app import app
from capital_cli.core.errors import SessionError

# Recognizable secret literals seeded into config so we can assert they never
# appear anywhere in the doctor output (human or --json).
_SECRET_API_KEY = "SECRET-KEY-123"
_SECRET_API_PASSWORD = "SECRET-PW-123"
_SECRET_IDENTIFIER = "secret@example.com"
_SECRET_LITERALS = (_SECRET_API_KEY, _SECRET_API_PASSWORD, _SECRET_IDENTIFIER)


@pytest.fixture
def seed_secret_config(monkeypatch, tmp_path):
    """Load config with KNOWN secret values so leak assertions are meaningful."""
    env = tmp_path / "secret.env"
    env.write_text(
        "CAP_ENV=demo\n"
        f"CAP_API_KEY={_SECRET_API_KEY}\n"
        f"CAP_IDENTIFIER={_SECRET_IDENTIFIER}\n"
        f"CAP_API_PASSWORD={_SECRET_API_PASSWORD}\n"
    )
    monkeypatch.setenv("CAP_ENV_FILE", str(env))
    from capital_cli.core.config import reset_config

    reset_config()
    yield
    reset_config()


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
    # No redacted markers either — secrets are omitted entirely.
    blob = json.dumps(payload)
    assert "***REDACTED***" not in blob


def test_doctor_json_no_secret_leak(runner, seed_secret_config, mock_doctor_ok):
    """With known secrets seeded into config, none may appear in --json output."""
    result = runner.invoke(app, ["--json", "doctor"])
    assert result.exit_code == 0, result.stdout
    # Sanity: the report was actually produced from the seeded config.
    payload = json.loads(result.stdout)
    assert payload["credentials_ok"] is True
    # The literal secret values must never appear in the doctor output.
    for secret in _SECRET_LITERALS:
        assert secret not in result.stdout, f"secret leaked into --json output: {secret!r}"


def test_doctor_human_ok(runner, mock_doctor_ok):
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0, result.stdout
    assert "env" in result.stdout.lower() or "demo" in result.stdout.lower()


def test_doctor_human_no_secret_leak(runner, seed_secret_config, mock_doctor_ok):
    """With known secrets seeded into config, none may appear in human output."""
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0, result.stdout
    for secret in _SECRET_LITERALS:
        assert secret not in result.stdout, f"secret leaked into human output: {secret!r}"


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
