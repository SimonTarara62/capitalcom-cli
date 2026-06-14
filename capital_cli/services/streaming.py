"""StreamService — presentation-free async iterators over the WebSocket stream.

Each method moves the ensure_logged_in + subscribe + parse/yield logic out of
``cli/stream_cmds.py``. It yields typed core models (PriceTick / OHLCBar /
StreamAlert) and contains NO rendering: no Typer, Rich, or ``out``. The CLI keeps
the NDJSON / Rich ``Live`` loop and just consumes these iterators; the SDK can
consume them too.

The WebSocket lifecycle is preserved exactly as the CLI had it: each generator
opens the client with ``async with ws:`` so the connection is connected on entry
and closed/unsubscribed on exit — including when the consumer stops iterating
early (e.g. ``alerts`` auto-close) or an exception propagates, because exiting
the ``async for`` body triggers the generator's ``aclose()`` which unwinds the
``async with``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from capital_cli.core.models import OHLCBar, PriceTick, StreamAlert
from capital_cli.core.session import get_session_manager
from capital_cli.core.websocket_client import get_websocket_client


class StreamService:
    """Async-iterator streaming domain service."""

    async def prices(
        self, epics: list[str], *, duration: float = 300.0
    ) -> AsyncIterator[PriceTick]:
        """Subscribe to and yield live price ticks for ``epics`` until ``duration``."""
        await get_session_manager().ensure_logged_in()
        ws = get_websocket_client()
        async with ws:
            await ws.subscribe(epics)
            async for tick in ws.stream(duration=duration):
                yield tick

    async def candles(
        self,
        epics: list[str],
        resolutions: list[str],
        *,
        bar_type: str = "classic",
        duration: float = 300.0,
    ) -> AsyncIterator[OHLCBar]:
        """Subscribe to and yield live OHLC bars until ``duration``."""
        await get_session_manager().ensure_logged_in()
        ws = get_websocket_client()
        async with ws:
            await ws.subscribe_ohlc(epics, resolutions, bar_type)
            async for bar in ws.stream_ohlc(duration=duration):
                yield bar

    async def portfolio(
        self, epics: list[str], *, duration: float = 300.0
    ) -> AsyncIterator[PriceTick]:
        """Subscribe to and yield live price ticks for the given position EPICs.

        The CLI resolves open-position EPICs via HTTP and aggregates ticks into
        portfolio snapshots; this iterator only handles the subscribe + stream
        half so the snapshot/throttle/render logic can stay in the CLI byte-for-
        byte.
        """
        await get_session_manager().ensure_logged_in()
        ws = get_websocket_client()
        async with ws:
            await ws.subscribe(epics)
            async for tick in ws.stream(duration=duration):
                yield tick

    async def alerts(
        self,
        epic: str,
        level: float,
        *,
        direction: str = "ABOVE",
        auto_close: bool = True,
        duration: float = 300.0,
    ) -> AsyncIterator[StreamAlert]:
        """Yield a StreamAlert each time ``epic``'s mid crosses ``level``.

        Stops after the first crossing when ``auto_close`` is set. ``direction``
        must already be normalised to ``ABOVE`` or ``BELOW`` by the caller.
        """
        await get_session_manager().ensure_logged_in()
        ws = get_websocket_client()
        async with ws:
            await ws.subscribe([epic])
            async for tick in ws.stream(duration=duration):
                mid = (tick.bid + tick.offer) / 2
                hit = (direction == "ABOVE" and mid >= level) or (
                    direction == "BELOW" and mid <= level
                )
                if hit:
                    yield StreamAlert(
                        epic=tick.epic,
                        condition=f"LEVEL_{direction}",
                        trigger_price=level,
                        current_price=mid,
                        timestamp=tick.timestamp,
                    )
                    if auto_close:
                        break
