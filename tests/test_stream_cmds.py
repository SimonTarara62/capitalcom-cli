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
    lines = [ln for ln in result.stdout.strip().splitlines() if ln.strip()]
    assert len(lines) >= 1
    for ln in lines:
        obj = json.loads(ln)
        assert obj["epic"] == "GOLD"
    assert mock_stream.subscribed == ["GOLD"]


def test_stream_prices_rejects_too_many(runner, mock_stream):
    epics = ",".join(f"E{i}" for i in range(41))
    result = runner.invoke(app, ["stream", "prices", epics])
    assert result.exit_code != 0


class _FakeOHLCWS:
    """Async context manager yielding canned OHLC bars then stopping."""

    def __init__(self, bars):
        self._bars = bars
        self.ohlc_sub = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return None

    async def subscribe_ohlc(self, epics, resolutions, bar_type="classic"):
        self.ohlc_sub = (epics, resolutions, bar_type)

    async def stream_ohlc(self, duration=300.0):
        for b in self._bars:
            yield b


@pytest.fixture
def mock_ohlc_stream(monkeypatch):
    from capital_cli.core.models import OHLCBar

    sm = MagicMock()
    sm.ensure_logged_in = AsyncMock()
    monkeypatch.setattr("capital_cli.cli.stream_cmds.get_session_manager", lambda: sm)

    bars = [
        OHLCBar(
            epic="BTCUSD",
            resolution="MINUTE",
            type="classic",
            price_type="bid",
            timestamp="2026-06-13T00:00:00Z",
            open=1.0,
            high=2.0,
            low=0.5,
            close=1.5,
        )
    ]
    fake = _FakeOHLCWS(bars)
    monkeypatch.setattr("capital_cli.cli.stream_cmds.get_websocket_client", lambda: fake)
    return fake


def test_stream_candles_collects_bars(runner, mock_ohlc_stream):
    result = runner.invoke(
        app, ["--json", "stream", "candles", "BTCUSD", "--resolution", "MINUTE", "--duration", "1"]
    )
    assert result.exit_code == 0
    lines = [ln for ln in result.stdout.strip().splitlines() if ln.strip()]
    assert len(lines) >= 1
    for ln in lines:
        obj = json.loads(ln)
        assert obj["resolution"] == "MINUTE"
        assert obj["type"] == "classic"
    assert mock_ohlc_stream.ohlc_sub == (["BTCUSD"], ["MINUTE"], "classic")


def test_stream_candles_rejects_bad_type(runner, mock_ohlc_stream):
    result = runner.invoke(app, ["stream", "candles", "BTCUSD", "--type", "invalid"])
    assert result.exit_code != 0


@pytest.fixture
def mock_stream_three(monkeypatch):
    sm = MagicMock()
    sm.ensure_logged_in = AsyncMock()
    monkeypatch.setattr("capital_cli.cli.stream_cmds.get_session_manager", lambda: sm)

    ticks = [
        PriceTick(epic="GOLD", bid=2000.0, offer=2001.0, timestamp="2026-06-12T00:00:00Z"),
        PriceTick(epic="GOLD", bid=2002.0, offer=2003.0, timestamp="2026-06-12T00:00:01Z"),
        PriceTick(epic="GOLD", bid=2004.0, offer=2005.0, timestamp="2026-06-12T00:00:02Z"),
    ]
    fake = _FakeWS(ticks)
    monkeypatch.setattr("capital_cli.cli.stream_cmds.get_websocket_client", lambda: fake)
    return fake


def test_stream_prices_ndjson_one_line_per_tick(monkeypatch, mock_stream_three, capsys):
    """In --json mode each tick is emitted as its own parseable JSON line."""
    import sys

    from typer.main import get_command

    from capital_cli.cli.app import app as real_app

    # Use a real stdout (not CliRunner's mixed capture) so we can count lines.
    monkeypatch.setattr(sys, "argv", ["capctl"])
    try:
        get_command(real_app)(
            ["--json", "stream", "prices", "GOLD", "--duration", "1", "--interval", "0"],
            standalone_mode=False,
        )
    except SystemExit:
        pass
    captured = capsys.readouterr()
    lines = [ln for ln in captured.out.strip().splitlines() if ln.strip()]
    assert len(lines) == 3
    for ln in lines:
        obj = json.loads(ln)
        assert obj["epic"] == "GOLD"
