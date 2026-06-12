"""capctl watchlist ... — watchlists."""

from __future__ import annotations

from typing import Any

import typer

from capital_cli.cli.runner import run
from capital_cli.core.config import get_config
from capital_cli.core.errors import ConfirmRequiredError
from capital_cli.core.http_client import get_client
from capital_cli.core.session import get_session_manager

app = typer.Typer(no_args_is_help=True, help="Watchlists: list, create, add, remove.")


def _require_confirm(yes: bool) -> None:
    if get_config().cap_require_explicit_confirm and not yes:
        raise ConfirmRequiredError()


@app.command("list")
def list_watchlists(ctx: typer.Context) -> None:
    """List all watchlists."""
    out = ctx.obj.out
    sm = get_session_manager()
    client = get_client()

    async def _do() -> dict[str, Any]:
        await sm.ensure_logged_in()
        return (await client.get("/watchlists")).json()

    data = run(out, _do, label="watchlist list")
    if out.json_mode:
        out.raw(data)
    else:
        out.rows(data.get("watchlists", []), ["id", "name"], title="Watchlists")


@app.command()
def get(ctx: typer.Context, watchlist_id: str = typer.Argument(..., help="Watchlist ID.")) -> None:
    """Get a watchlist and its markets."""
    out = ctx.obj.out
    sm = get_session_manager()
    client = get_client()

    async def _do() -> dict[str, Any]:
        await sm.ensure_logged_in()
        return (await client.get(f"/watchlists/{watchlist_id}")).json()

    out.raw(run(out, _do, label="watchlist get"))


@app.command()
def create(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Watchlist name."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm creation."),
) -> None:
    """Create a new watchlist."""
    out = ctx.obj.out
    sm = get_session_manager()
    client = get_client()

    async def _do() -> dict[str, Any]:
        _require_confirm(yes)
        await sm.ensure_logged_in()
        return (await client.post("/watchlists", json={"name": name})).json()

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
    sm = get_session_manager()
    client = get_client()

    async def _do() -> dict[str, Any]:
        _require_confirm(yes)
        await sm.ensure_logged_in()
        return (await client.put(f"/watchlists/{watchlist_id}", json={"epic": epic})).json()

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
    sm = get_session_manager()
    client = get_client()

    async def _do() -> dict[str, Any]:
        _require_confirm(yes)
        await sm.ensure_logged_in()
        resp = await client.delete(f"/watchlists/{watchlist_id}/{epic}")
        return resp.json() if resp.text else {"status": "removed"}

    out.record(run(out, _do, label="watchlist remove"), title="Removed from watchlist")


@app.command()
def delete(
    ctx: typer.Context,
    watchlist_id: str = typer.Argument(..., help="Watchlist ID."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm deletion."),
) -> None:
    """Delete a watchlist."""
    out = ctx.obj.out
    sm = get_session_manager()
    client = get_client()

    async def _do() -> dict[str, Any]:
        _require_confirm(yes)
        await sm.ensure_logged_in()
        resp = await client.delete(f"/watchlists/{watchlist_id}")
        return resp.json() if resp.text else {"status": "deleted"}

    out.record(run(out, _do, label="watchlist delete"), title="Deleted watchlist")
