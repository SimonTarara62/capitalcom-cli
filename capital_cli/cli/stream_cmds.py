"""capctl stream ... — real-time WebSocket streaming."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import typer
from rich.live import Live
from rich.table import Table

from capital_cli.cli.runner import run
from capital_cli.core.session import get_session_manager
from capital_cli.services.streaming import StreamService

app = typer.Typer(no_args_is_help=True, help="Real-time streaming: prices, alerts, portfolio.")


def _parse_epics(raw: str) -> list[str]:
    epics = [e.strip() for e in raw.split(",") if e.strip()]
    if not epics:
        raise typer.BadParameter("Provide at least one EPIC.")
    if len(epics) > 40:
        raise typer.BadParameter(f"Capital.com allows at most 40 EPICs (got {len(epics)}).")
    return epics


def _price_table(latest: dict[str, Any]) -> Table:
    table = Table(title="Live prices (Ctrl-C to stop)", header_style="bold cyan")
    for col in ["epic", "bid", "offer", "timestamp"]:
        table.add_column(col)
    for epic in sorted(latest):
        tick = latest[epic]
        table.add_row(epic, str(tick["bid"]), str(tick["offer"]), tick["timestamp"])
    return table


def _candle_table(latest: dict[str, Any]) -> Table:
    table = Table(title="Live candles (Ctrl-C to stop)", header_style="bold cyan")
    for col in ["epic", "resolution", "open", "high", "low", "close", "timestamp"]:
        table.add_column(col)
    for key in sorted(latest):
        b = latest[key]
        table.add_row(
            b["epic"],
            b["resolution"],
            str(b["open"]),
            str(b["high"]),
            str(b["low"]),
            str(b["close"]),
            b["timestamp"],
        )
    return table


@app.command()
def prices(
    ctx: typer.Context,
    epics: str = typer.Argument(..., help="Comma-separated EPICs (max 40)."),
    duration: float = typer.Option(300.0, "--duration", help="Stream duration in seconds."),
    interval: float = typer.Option(1.0, "--interval", help="Min seconds between recorded updates."),
) -> None:
    """Stream live bid/offer prices.

    With --json, emits NDJSON: one compact JSON object per tick to stdout as it
    arrives (flushed per line), suitable for an agent/script watch-loop.
    """
    out = ctx.obj.out
    parsed = _parse_epics(epics)

    async def _do() -> dict[str, Any]:
        collected: list[dict[str, Any]] = []
        latest: dict[str, Any] = {}
        last_emit = datetime.now(timezone.utc)
        live = (
            None
            if out.json_mode
            else Live(_price_table(latest), console=out.console, refresh_per_second=4)
        )
        if live:
            live.__enter__()
        try:
            async for tick in StreamService().prices(parsed, duration=duration):
                row = tick.model_dump()
                latest[row["epic"]] = row
                now = datetime.now(timezone.utc)
                if (now - last_emit).total_seconds() >= interval:
                    collected.append(row)
                    last_emit = now
                    if out.json_mode:
                        out.json_line(row)
                if live:
                    live.update(_price_table(latest))
        finally:
            if live:
                live.__exit__(None, None, None)
        return {
            "epics": parsed,
            "duration_s": duration,
            "ticks_received": len(collected),
            "ticks": collected[-100:],
        }

    data = run(out, _do, label="stream prices")
    if not out.json_mode:
        out.note(f"Collected {data['ticks_received']} updates over {data['duration_s']}s.")


@app.command()
def alerts(
    ctx: typer.Context,
    epic: str = typer.Argument(..., help="Market EPIC to watch."),
    level: float = typer.Argument(..., help="Trigger price level."),
    direction: str = typer.Option("ABOVE", "--direction", help="ABOVE or BELOW."),
    duration: float = typer.Option(300.0, "--duration", help="Max monitoring seconds."),
    auto_close: bool = typer.Option(
        True, "--auto-close/--keep-open", help="Stop after first trigger."
    ),
) -> None:
    """Trigger an alert when a market crosses a price level."""
    out = ctx.obj.out
    direction_u = direction.upper()
    if direction_u not in ("ABOVE", "BELOW"):
        raise typer.BadParameter("--direction must be ABOVE or BELOW.")

    async def _do() -> dict[str, Any]:
        triggered: list[dict[str, Any]] = []
        async for alert in StreamService().alerts(
            epic,
            level,
            direction=direction_u,
            auto_close=auto_close,
            duration=duration,
        ):
            event = alert.model_dump()
            triggered.append(event)
            if out.json_mode:
                out.json_line(event)
            else:
                out.success(
                    f"ALERT {alert.epic} {direction_u} {level} (now {alert.current_price:.2f})"
                )
        return {"epic": epic, "level": level, "direction": direction_u, "triggered": triggered}

    data = run(out, _do, label="stream alerts")
    if out.json_mode:
        # NDJSON: the crossing event (if any) was already emitted as its own line
        # above. Emit the final summary too so a non-triggering run still yields a
        # parseable object.
        if not data["triggered"]:
            out.json_line(data)
    elif not data["triggered"]:
        out.note("No alert triggered within the duration.")


@app.command()
def portfolio(
    ctx: typer.Context,
    duration: float = typer.Option(300.0, "--duration", help="Stream duration in seconds."),
    interval: float = typer.Option(5.0, "--interval", help="Recording interval in seconds."),
) -> None:
    """Stream live price snapshots for currently open positions.

    With --json, emits NDJSON: one compact JSON object per snapshot to stdout as
    it arrives (flushed per line).
    """
    out = ctx.obj.out
    from capital_cli.core.http_client import get_client

    async def _do() -> dict[str, Any]:
        sm = get_session_manager()
        await sm.ensure_logged_in()
        client = get_client()
        positions = (await client.get("/positions")).json().get("positions", [])
        epics = [
            p.get("market", {}).get("epic") for p in positions if p.get("market", {}).get("epic")
        ]
        if not epics:
            return {"positions": 0, "note": "No open positions to stream."}
        snapshots: list[dict[str, Any]] = []
        last_emit = datetime.now(timezone.utc)
        latest: dict[str, Any] = {}
        async for tick in StreamService().portfolio(epics[:40], duration=duration):
            latest[tick.epic] = (tick.bid + tick.offer) / 2
            now = datetime.now(timezone.utc)
            if (now - last_emit).total_seconds() >= interval:
                snapshot = {"prices": dict(latest), "timestamp": tick.timestamp}
                snapshots.append(snapshot)
                last_emit = now
                if out.json_mode:
                    out.json_line(snapshot)
        return {"positions": len(epics), "snapshots": snapshots[-50:]}

    data = run(out, _do, label="stream portfolio")
    if not out.json_mode:
        out.raw(data)


@app.command()
def candles(
    ctx: typer.Context,
    epics: str = typer.Argument(..., help="Comma-separated EPICs (max 40)."),
    resolution: str = typer.Option(
        "MINUTE",
        "--resolution",
        help="MINUTE, MINUTE_5, MINUTE_15, MINUTE_30, HOUR, HOUR_4, DAY, WEEK.",
    ),
    bar_type: str = typer.Option("classic", "--type", help="classic or heikin-ashi."),
    duration: float = typer.Option(300.0, "--duration", help="Stream duration in seconds."),
    interval: float = typer.Option(
        0.0, "--interval", help="Min seconds between recorded bars (0 = every update)."
    ),
) -> None:
    """Stream live OHLC candlesticks.

    With --json, emits NDJSON: one compact JSON object per bar to stdout as it
    arrives (flushed per line).
    """
    out = ctx.obj.out
    parsed = _parse_epics(epics)
    if bar_type not in ("classic", "heikin-ashi"):
        raise typer.BadParameter("--type must be classic or heikin-ashi.")

    async def _do() -> dict[str, Any]:
        collected: list[dict[str, Any]] = []
        latest: dict[str, Any] = {}
        last_emit = datetime.now(timezone.utc)
        live = (
            None
            if out.json_mode
            else Live(_candle_table(latest), console=out.console, refresh_per_second=4)
        )
        if live:
            live.__enter__()
        try:
            async for bar in StreamService().candles(
                parsed, [resolution], bar_type=bar_type, duration=duration
            ):
                row = bar.model_dump()
                latest[f"{row['epic']}:{row['resolution']}"] = row
                now = datetime.now(timezone.utc)
                if (now - last_emit).total_seconds() >= interval:
                    collected.append(row)
                    last_emit = now
                    if out.json_mode:
                        out.json_line(row)
                if live:
                    live.update(_candle_table(latest))
        finally:
            if live:
                live.__exit__(None, None, None)
        return {
            "epics": parsed,
            "resolution": resolution,
            "type": bar_type,
            "duration_s": duration,
            "bars_received": len(collected),
            "bars": collected[-100:],
        }

    data = run(out, _do, label="stream candles")
    if not out.json_mode:
        out.note(f"Collected {data['bars_received']} candles over {data['duration_s']}s.")
