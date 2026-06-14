from unittest.mock import AsyncMock, MagicMock

import pytest

from capital_cli.cli.app import app


@pytest.fixture
def mock_wl(monkeypatch):
    sm = MagicMock()
    sm.ensure_logged_in = AsyncMock()
    monkeypatch.setattr("capital_cli.services.watchlists.get_session_manager", lambda: sm)

    client = MagicMock()
    resp = MagicMock()
    resp.json = MagicMock(return_value={"watchlists": [{"id": "1", "name": "Metals"}]})
    resp.text = "{}"
    client.get = AsyncMock(return_value=resp)
    client.post = AsyncMock(return_value=resp)
    client.put = AsyncMock(return_value=resp)
    client.delete = AsyncMock(return_value=resp)
    monkeypatch.setattr("capital_cli.services.watchlists.get_client", lambda: client)
    return client


def test_list(runner, mock_wl):
    result = runner.invoke(app, ["watchlist", "list"])
    assert result.exit_code == 0
    assert "Metals" in result.stdout


def test_create_requires_confirm(runner, mock_wl):
    result = runner.invoke(app, ["watchlist", "create", "Crypto"])
    assert result.exit_code == 4
    mock_wl.post.assert_not_awaited()


def test_create_with_yes(runner, mock_wl):
    result = runner.invoke(app, ["watchlist", "create", "Crypto", "--yes"])
    assert result.exit_code == 0
    assert mock_wl.post.await_args.kwargs["json"] == {"name": "Crypto"}


def test_add_with_yes(runner, mock_wl):
    result = runner.invoke(app, ["watchlist", "add", "1", "GOLD", "--yes"])
    assert result.exit_code == 0
    assert mock_wl.put.await_args.args[0] == "/watchlists/1"
    assert mock_wl.put.await_args.kwargs["json"] == {"epic": "GOLD"}
