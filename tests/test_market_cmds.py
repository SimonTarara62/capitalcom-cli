import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from capital_cli.cli.app import app


@pytest.fixture
def mock_market(monkeypatch):
    sm = MagicMock()
    sm.ensure_logged_in = AsyncMock()
    monkeypatch.setattr("capital_cli.services.markets.get_session_manager", lambda: sm)

    client = MagicMock()
    resp = MagicMock()
    resp.json = MagicMock(
        return_value={
            "markets": [
                {"epic": "GOLD", "instrumentName": "Gold", "bid": 2000.0, "offer": 2001.0},
                {"epic": "SILVER", "instrumentName": "Silver", "bid": 25.0, "offer": 25.1},
            ]
        }
    )
    client.get = AsyncMock(return_value=resp)
    monkeypatch.setattr("capital_cli.services.markets.get_client", lambda: client)
    return client


def test_search_table(runner, mock_market):
    result = runner.invoke(app, ["market", "search", "gold"])
    assert result.exit_code == 0
    assert "GOLD" in result.stdout
    mock_market.get.assert_awaited()


def test_search_json(runner, mock_market):
    result = runner.invoke(app, ["--json", "market", "search", "gold"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["markets"][0]["epic"] == "GOLD"


def test_get_calls_epic_path(runner, mock_market):
    result = runner.invoke(app, ["market", "get", "GOLD"])
    assert result.exit_code == 0
    assert mock_market.get.await_args.args[0] == "/markets/GOLD"


def test_prices_passes_resolution(runner, mock_market):
    result = runner.invoke(
        app, ["--json", "market", "prices", "GOLD", "--resolution", "HOUR", "--max", "10"]
    )
    assert result.exit_code == 0
    assert mock_market.get.await_args.kwargs["params"]["resolution"] == "HOUR"
    assert mock_market.get.await_args.kwargs["params"]["max"] == 10


def test_sentiment_single(runner, mock_market):
    mock_market.get.return_value.json.return_value = {
        "marketId": "GOLD",
        "longPositionPercentage": 60.0,
        "shortPositionPercentage": 40.0,
    }
    result = runner.invoke(app, ["--json", "market", "sentiment", "GOLD"])
    assert result.exit_code == 0
    assert mock_market.get.await_args.args[0] == "/clientsentiment/GOLD"
    assert json.loads(result.stdout)["marketId"] == "GOLD"


def test_sentiment_batch(runner, mock_market):
    mock_market.get.return_value.json.return_value = {
        "clientSentiments": [
            {"marketId": "GOLD", "longPositionPercentage": 60.0, "shortPositionPercentage": 40.0},
            {"marketId": "SILVER", "longPositionPercentage": 55.0, "shortPositionPercentage": 45.0},
        ]
    }
    result = runner.invoke(app, ["--json", "market", "sentiment", "GOLD,SILVER"])
    assert result.exit_code == 0
    assert mock_market.get.await_args.args[0] == "/clientsentiment"
    assert mock_market.get.await_args.kwargs["params"] == {"marketIds": "GOLD,SILVER"}


def test_nav_node_limit(runner, mock_market):
    mock_market.get.return_value.json.return_value = {"nodes": []}
    result = runner.invoke(
        app, ["--json", "market", "nav-node", "hierarchy_v1.commodities", "--limit", "10"]
    )
    assert result.exit_code == 0
    assert mock_market.get.await_args.args[0] == "/marketnavigation/hierarchy_v1.commodities"
    assert mock_market.get.await_args.kwargs["params"] == {"limit": 10}
