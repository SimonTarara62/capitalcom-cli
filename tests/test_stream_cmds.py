import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from capital_cli.cli.app import app
from capital_cli.core.models import PriceTick


class _FakeWS:
    """Async context manager yielding canned ticks then stopping."""

    def __init__(self, ticks):
        self._ticks = ticks
        self.subscribed = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return None

    async def subscribe(self, epics):
        self.subscribed = epics

    async def stream(self, duration=300.0):
        for t in self._ticks:
            yield t


@pytest.fixture
def mock_stream(monkeypatch):
    sm = MagicMock()
    sm.ensure_logged_in = AsyncMock()
    monkeypatch.setattr("capital_cli.cli.stream_cmds.get_session_manager", lambda: sm)

    ticks = [
        PriceTick(epic="GOLD", bid=2000.0, offer=2001.0, timestamp="2026-06-12T00:00:00Z"),
        PriceTick(epic="GOLD", bid=2002.0, offer=2003.0, timestamp="2026-06-12T00:00:01Z"),
    ]
    fake = _FakeWS(ticks)
    monkeypatch.setattr("capital_cli.cli.stream_cmds.get_websocket_client", lambda: fake)
    return fake


def test_stream_prices_collects_ticks(runner, mock_stream):
    result = runner.invoke(
        app, ["--json", "stream", "prices", "GOLD", "--duration", "1", "--interval", "0"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["epics"] == ["GOLD"]
    assert payload["ticks_received"] >= 1
    assert mock_stream.subscribed == ["GOLD"]


def test_stream_prices_rejects_too_many(runner, mock_stream):
    epics = ",".join(f"E{i}" for i in range(41))
    result = runner.invoke(app, ["stream", "prices", epics])
    assert result.exit_code != 0
