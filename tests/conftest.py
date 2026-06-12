"""Shared fixtures for CLI command tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from typer.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def _credentials(monkeypatch, tmp_path):
    """Provide valid credentials via env so get_config() never fails."""
    env = tmp_path / "test.env"
    env.write_text(
        "CAP_ENV=demo\nCAP_API_KEY=k\nCAP_IDENTIFIER=a@b.c\nCAP_API_PASSWORD=p\n"
    )
    monkeypatch.setenv("CAP_ENV_FILE", str(env))
    from capital_cli.core.config import reset_config

    reset_config()
    yield
    reset_config()


@pytest.fixture
def mock_session(monkeypatch):
    """Patch get_session_manager in session_cmds with an AsyncMock."""
    sm = MagicMock()
    sm.login = AsyncMock(return_value={"currentAccountId": "ACC1"})
    sm.account_id = "ACC1"
    sm.switch_account = AsyncMock(return_value={"trailingStopsEnabled": False})
    sm.ping = AsyncMock(return_value={"status": "OK"})
    sm.logout = AsyncMock(return_value=None)
    sm.ensure_logged_in = AsyncMock()
    status = MagicMock()
    status.model_dump = MagicMock(
        return_value={
            "env": "demo",
            "base_url": "https://demo-api-capital.backend-capital.com",
            "logged_in": True,
            "account_id": "ACC1",
        }
    )
    sm.get_status = MagicMock(return_value=status)
    monkeypatch.setattr("capital_cli.cli.session_cmds.get_session_manager", lambda: sm)
    return sm
