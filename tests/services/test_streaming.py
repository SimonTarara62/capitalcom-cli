"""Tests locking StreamService to the same subscribe + stream behaviour the CLI had.

The service exposes async iterators of typed models (PriceTick / OHLCBar /
StreamAlert) and contains NO rendering. It must call ensure_logged_in, subscribe
with the same params, iterate the WebSocket stream, and respect the same
duration/stop semantics — without any Typer/Rich/output.
"""

from __future__ import annotations

from typing import Any

import pytest

from capital_cli.core.models import OHLCBar, PriceTick, StreamAlert
from capital_cli.services.streaming import StreamService


class _FakeWS:
    """Async context manager yielding canned ticks then stopping."""

    def __init__(self, ticks: list[PriceTick]) -> None:
        self._ticks = ticks
        self.subscribed: list[str] | None = None
        self.entered = False
        self.exited = False

    async def __aenter__(self) -> _FakeWS:
        self.entered = True
        return self

    async def __aexit__(self, *a: Any) -> None:
        self.exited = True

    async def subscribe(self, epics: list[str]) -> None:
        self.subscribed = epics

    async def stream(self, duration: float = 300.0):
        for t in self._ticks:
            yield t


class _FakeOHLCWS:
    def __init__(self, bars: list[OHLCBar]) -> None:
        self._bars = bars
        self.ohlc_sub: tuple[Any, ...] | None = None
        self.exited = False

    async def __aenter__(self) -> _FakeOHLCWS:
        return self

    async def __aexit__(self, *a: Any) -> None:
        self.exited = True

    async def subscribe_ohlc(
        self, epics: list[str], resolutions: list[str], bar_type: str = "classic"
    ) -> None:
        self.ohlc_sub = (epics, resolutions, bar_type)

    async def stream_ohlc(self, duration: float = 300.0):
        for b in self._bars:
            yield b


class _FakeSession:
    def __init__(self) -> None:
        self.logged_in = 0

    async def ensure_logged_in(self) -> None:
        self.logged_in += 1


@pytest.fixture
def wired(monkeypatch):
    def _wire(ws: Any):
        session = _FakeSession()
        monkeypatch.setattr(
            "capital_cli.services.streaming.get_session_manager", lambda: session
        )
        monkeypatch.setattr(
            "capital_cli.services.streaming.get_websocket_client", lambda: ws
        )
        return session

    return _wire


@pytest.mark.asyncio
async def test_prices_yields_typed_ticks(wired):
    ticks = [
        PriceTick(epic="GOLD", bid=2000.0, offer=2001.0, timestamp="2026-06-12T00:00:00Z"),
        PriceTick(epic="GOLD", bid=2002.0, offer=2003.0, timestamp="2026-06-12T00:00:01Z"),
    ]
    ws = _FakeWS(ticks)
    session = wired(ws)

    out = [t async for t in StreamService().prices(["GOLD"], duration=1.0)]

    assert len(out) == 2
    assert all(isinstance(t, PriceTick) for t in out)
    assert out[0].epic == "GOLD"
    assert ws.subscribed == ["GOLD"]
    assert ws.exited is True  # connection torn down via the context manager
    assert session.logged_in == 1


@pytest.mark.asyncio
async def test_candles_yields_typed_bars(wired):
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
    ws = _FakeOHLCWS(bars)
    wired(ws)

    out = [b async for b in StreamService().candles(["BTCUSD"], ["MINUTE"], duration=1.0)]

    assert len(out) == 1
    assert isinstance(out[0], OHLCBar)
    assert ws.ohlc_sub == (["BTCUSD"], ["MINUTE"], "classic")
    assert ws.exited is True


@pytest.mark.asyncio
async def test_alerts_yields_streamalert_on_crossing_and_stops(wired):
    ticks = [
        PriceTick(epic="GOLD", bid=1990.0, offer=1992.0, timestamp="2026-06-12T00:00:00Z"),
        PriceTick(epic="GOLD", bid=2010.0, offer=2012.0, timestamp="2026-06-12T00:00:01Z"),
        PriceTick(epic="GOLD", bid=2020.0, offer=2022.0, timestamp="2026-06-12T00:00:02Z"),
    ]
    ws = _FakeWS(ticks)
    wired(ws)

    out = [
        a
        async for a in StreamService().alerts(
            "GOLD", 2000.0, direction="ABOVE", auto_close=True, duration=1.0
        )
    ]

    assert len(out) == 1  # auto_close stops after the first trigger
    assert isinstance(out[0], StreamAlert)
    assert out[0].condition == "LEVEL_ABOVE"
    assert out[0].epic == "GOLD"
    assert ws.subscribed == ["GOLD"]


@pytest.mark.asyncio
async def test_alerts_keep_open_yields_all_crossings(wired):
    ticks = [
        PriceTick(epic="GOLD", bid=2010.0, offer=2012.0, timestamp="2026-06-12T00:00:01Z"),
        PriceTick(epic="GOLD", bid=2020.0, offer=2022.0, timestamp="2026-06-12T00:00:02Z"),
    ]
    ws = _FakeWS(ticks)
    wired(ws)

    out = [
        a
        async for a in StreamService().alerts(
            "GOLD", 2000.0, direction="ABOVE", auto_close=False, duration=1.0
        )
    ]

    assert len(out) == 2
