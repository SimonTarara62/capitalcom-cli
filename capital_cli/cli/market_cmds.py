"""capctl market ... — market data."""

from __future__ import annotations

from typing import Any

import typer

from capital_cli.cli.runner import run
from capital_cli.services.markets import MarketService

app = typer.Typer(no_args_is_help=True, help="Market data: search, prices, sentiment.")


@app.command()
def search(
    ctx: typer.Context,
    term: str | None = typer.Argument(None, help="Search term, e.g. 'Bitcoin'."),
    epics: str | None = typer.Option(None, "--epics", help="Comma-separated EPICs to filter."),
    limit: int = typer.Option(50, "--limit", help="Max results."),
) -> None:
    """Search markets by term or EPICs."""
    out = ctx.obj.out

    async def _do() -> dict[str, Any]:
        return await MarketService().search(term, epics=epics, limit=limit)

    data = run(out, _do, label="market search")
    if out.json_mode:
        out.raw(data)
    else:
        out.rows(
            data.get("markets", []),
            ["epic", "instrumentName", "bid", "offer", "marketStatus"],
            title="Markets",
        )


@app.command()
def get(ctx: typer.Context, epic: str = typer.Argument(..., help="Market EPIC.")) -> None:
    """Get full market details and dealing rules."""
    out = ctx.obj.out

    async def _do() -> dict[str, Any]:
        return await MarketService().get(epic)

    out.raw(run(out, _do, label="market get"))


@app.command("nav-root")
def nav_root(ctx: typer.Context) -> None:
    """Get the root market-navigation tree."""
    out = ctx.obj.out

    async def _do() -> dict[str, Any]:
        return await MarketService().navigation_root()

    data = run(out, _do, label="market nav-root")
    if out.json_mode:
        out.raw(data)
    else:
        out.rows(data.get("nodes", []), ["id", "name"], title="Market categories")


@app.command("nav-node")
def nav_node(
    ctx: typer.Context,
    node_id: str = typer.Argument(..., help="Navigation node ID."),
    limit: int | None = typer.Option(None, "--limit", help="Max child nodes/markets (<=500)."),
) -> None:
    """Get child nodes/markets under a navigation node."""
    out = ctx.obj.out

    async def _do() -> dict[str, Any]:
        return await MarketService().navigation_node(node_id, limit=limit)

    out.raw(run(out, _do, label="market nav-node"))


@app.command()
def prices(
    ctx: typer.Context,
    epic: str = typer.Argument(..., help="Market EPIC."),
    resolution: str = typer.Option(
        "MINUTE_15",
        "--resolution",
        help="MINUTE, MINUTE_5, MINUTE_15, MINUTE_30, HOUR, HOUR_4, DAY, WEEK.",
    ),
    max_candles: int = typer.Option(200, "--max", help="Max candles (<=1000)."),
    from_date: str | None = typer.Option(None, "--from", help="Start date ISO 8601."),
    to_date: str | None = typer.Option(None, "--to", help="End date ISO 8601."),
) -> None:
    """Get historical OHLC prices."""
    out = ctx.obj.out

    async def _do() -> dict[str, Any]:
        return await MarketService().prices(
            epic,
            resolution=resolution,
            max=max_candles,
            from_date=from_date,
            to_date=to_date,
        )

    out.raw(run(out, _do, label="market prices"))


@app.command()
def sentiment(
    ctx: typer.Context,
    market_ids: str = typer.Argument(
        ..., help="Market ID, or comma-separated IDs for a batch (e.g. 'GOLD,SILVER')."
    ),
) -> None:
    """Get client sentiment (long vs short %) for one or several markets."""
    out = ctx.obj.out
    ids = [m.strip() for m in market_ids.split(",") if m.strip()]
    if not ids:
        raise typer.BadParameter("Provide at least one market ID.")

    async def _do() -> dict[str, Any]:
        return await MarketService().sentiment(ids)

    data = run(out, _do, label="market sentiment")
    if out.json_mode:
        out.raw(data)
    elif len(ids) == 1:
        out.record(data, title=f"Sentiment: {ids[0]}")
    else:
        out.rows(
            data.get("clientSentiments", []),
            ["marketId", "longPositionPercentage", "shortPositionPercentage"],
            title="Client sentiment",
        )
