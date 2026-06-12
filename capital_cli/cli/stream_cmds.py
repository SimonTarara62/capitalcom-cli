"""capctl stream ... — real-time WebSocket streaming."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import typer
from rich.live import Live
from rich.table import Table

from capital_cli.cli.runner import run
from capital_cli.core.session import get_session_manager
from capital_cli.core.websocket_client import get_websocket_client

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


@app.command()
def prices(
    ctx: typer.Context,
    epics: str = typer.Argument(..., help="Comma-separated EPICs (max 40)."),
    duration: float = typer.Option(300.0, "--duration", help="Stream duration in seconds."),
    interval: float = typer.Option(
        1.0, "--interval", help="Min seconds between recorded updates."
    ),
) -> None:
    """Stream live bid/offer prices."""
    out = ctx.obj.out
    parsed = _parse_epics(epics)
    sm = get_session_manager()

    async def _do() -> dict[str, Any]:
        await sm.ensure_logged_in()
        collected: list[dict[str, Any]] = []
        latest: dict[str, Any] = {}
        last_emit = datetime.now(timezone.utc)
        ws = get_websocket_client()
        live = (
            None
            if out.json_mode
            else Live(_price_table(latest), console=out.console, refresh_per_second=4)
        )
        if live:
            live.__enter__()
        try:
            async with ws:
                await ws.subscribe(parsed)
                async for tick in ws.stream(duration=duration):
                    row = tick.model_dump()
                    latest[row["epic"]] = row
                    now = datetime.now(timezone.utc)
                    if (now - last_emit).total_seconds() >= interval:
                        collected.append(row)
                        last_emit = now
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
    if out.json_mode:
        out.raw(data)
    else:
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
    sm = get_session_manager()
    direction_u = direction.upper()
    if direction_u not in ("ABOVE", "BELOW"):
        raise typer.BadParameter("--direction must be ABOVE or BELOW.")

    async def _do() -> dict[str, Any]:
        await sm.ensure_logged_in()
        triggered: list[dict[str, Any]] = []
        ws = get_websocket_client()
        async with ws:
            await ws.subscribe([epic])
            async for tick in ws.stream(duration=duration):
                mid = (tick.bid + tick.offer) / 2
                hit = (direction_u == "ABOVE" and mid >= level) or (
                    direction_u == "BELOW" and mid <= level
                )
                if hit:
                    event = {
                        "epic": tick.epic,
                        "condition": f"LEVEL_{direction_u}",
                        "trigger_price": level,
                        "current_price": mid,
                        "timestamp": tick.timestamp,
                    }
                    triggered.append(event)
                    if not out.json_mode:
                        out.success(f"ALERT {tick.epic} {direction_u} {level} (now {mid:.2f})")
                    if auto_close:
                        break
        return {"epic": epic, "level": level, "direction": direction_u, "triggered": triggered}

    data = run(out, _do, label="stream alerts")
    if out.json_mode:
        out.raw(data)
    elif not data["triggered"]:
        out.note("No alert triggered within the duration.")


@app.command()
def portfolio(
    ctx: typer.Context,
    duration: float = typer.Option(300.0, "--duration", help="Stream duration in seconds."),
    interval: float = typer.Option(5.0, "--interval", help="Recording interval in seconds."),
) -> None:
    """Stream live price snapshots for currently open positions."""
    out = ctx.obj.out
    sm = get_session_manager()
    from capital_cli.core.http_client import get_client

    async def _do() -> dict[str, Any]:
        await sm.ensure_logged_in()
        client = get_client()
        positions = (await client.get("/positions")).json().get("positions", [])
        epics = [
            p.get("market", {}).get("epic")
            for p in positions
            if p.get("market", {}).get("epic")
        ]
        if not epics:
            return {"positions": 0, "note": "No open positions to stream."}
        snapshots: list[dict[str, Any]] = []
        last_emit = datetime.now(timezone.utc)
        latest: dict[str, Any] = {}
        ws = get_websocket_client()
        async with ws:
            await ws.subscribe(epics[:40])
            async for tick in ws.stream(duration=duration):
                latest[tick.epic] = (tick.bid + tick.offer) / 2
                now = datetime.now(timezone.utc)
                if (now - last_emit).total_seconds() >= interval:
                    snapshots.append({"prices": dict(latest), "timestamp": tick.timestamp})
                    last_emit = now
        return {"positions": len(epics), "snapshots": snapshots[-50:]}

    out.raw(run(out, _do, label="stream portfolio"))
