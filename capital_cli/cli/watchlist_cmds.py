"""capctl watchlist ... — watchlists."""

from __future__ import annotations

from typing import Any

import typer

from capital_cli.cli.runner import run
from capital_cli.services.watchlists import WatchlistService

app = typer.Typer(no_args_is_help=True, help="Watchlists: list, create, add, remove.")


@app.command("list")
def list_watchlists(ctx: typer.Context) -> None:
    """List all watchlists."""
    out = ctx.obj.out

    async def _do() -> dict[str, Any]:
        return await WatchlistService().list()

    data = run(out, _do, label="watchlist list")
    if out.json_mode:
        out.raw(data)
    else:
        out.rows(data.get("watchlists", []), ["id", "name"], title="Watchlists")


@app.command()
def get(ctx: typer.Context, watchlist_id: str = typer.Argument(..., help="Watchlist ID.")) -> None:
    """Get a watchlist and its markets."""
    out = ctx.obj.out

    async def _do() -> dict[str, Any]:
        return await WatchlistService().get(watchlist_id)

    out.raw(run(out, _do, label="watchlist get"))


@app.command()
def create(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Watchlist name."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm creation."),
) -> None:
    """Create a new watchlist."""
    out = ctx.obj.out

    async def _do() -> dict[str, Any]:
        return await WatchlistService().create(name, confirm=yes)

    out.record(run(out, _do, label="watchlist create"), title="Created watchlist")


@app.command()
def add(
    ctx: typer.Context,
    watchlist_id: str = typer.Argument(..., help="Watchlist ID."),
    epic: str = typer.Argument(..., help="Market EPIC to add."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm."),
) -> None:
    """Add a market to a watchlist."""
    out = ctx.obj.out

    async def _do() -> dict[str, Any]:
        return await WatchlistService().add_market(watchlist_id, epic, confirm=yes)

    out.record(run(out, _do, label="watchlist add"), title="Added to watchlist")


@app.command()
def remove(
    ctx: typer.Context,
    watchlist_id: str = typer.Argument(..., help="Watchlist ID."),
    epic: str = typer.Argument(..., help="Market EPIC to remove."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm."),
) -> None:
    """Remove a market from a watchlist."""
    out = ctx.obj.out

    async def _do() -> dict[str, Any]:
        return await WatchlistService().remove_market(watchlist_id, epic, confirm=yes)

    out.record(run(out, _do, label="watchlist remove"), title="Removed from watchlist")


@app.command()
def delete(
    ctx: typer.Context,
    watchlist_id: str = typer.Argument(..., help="Watchlist ID."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm deletion."),
) -> None:
    """Delete a watchlist."""
    out = ctx.obj.out

    async def _do() -> dict[str, Any]:
        return await WatchlistService().delete(watchlist_id, confirm=yes)

    out.record(run(out, _do, label="watchlist delete"), title="Deleted watchlist")
