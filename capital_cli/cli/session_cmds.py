"""capctl session ... — session lifecycle."""

from __future__ import annotations

import typer

from capital_cli.cli.runner import run
from capital_cli.core.session import get_session_manager

app = typer.Typer(no_args_is_help=True, help="Session lifecycle: login, ping, logout.")


@app.command()
def status(ctx: typer.Context) -> None:
    """Show current session status (no network call)."""
    out = ctx.obj.out
    sm = get_session_manager()
    out.record(sm.get_status().model_dump(), title="Session status")


@app.command()
def login(
    ctx: typer.Context,
    force: bool = typer.Option(False, "--force", help="Re-login even if a session is valid."),
    account: str | None = typer.Option(
        None, "--account", "-a", help="Account ID to switch to after login."
    ),
) -> None:
    """Create (or verify) a session and store auth tokens."""
    out = ctx.obj.out
    sm = get_session_manager()

    async def _do():
        data = await sm.login(force=force, account_id=account)
        data["active_account_id"] = sm.account_id
        return data

    data = run(out, _do, label="session login")
    out.record(
        {"active_account_id": data.get("active_account_id"), "status": "logged in"},
        title="Login",
    )


@app.command()
def ping(ctx: typer.Context) -> None:
    """Keep the session alive."""
    out = ctx.obj.out
    sm = get_session_manager()

    async def _do():
        await sm.ensure_logged_in()
        return await sm.ping()

    out.record(run(out, _do, label="session ping"), title="Ping")


@app.command()
def logout(ctx: typer.Context) -> None:
    """End the session and clear tokens."""
    out = ctx.obj.out
    sm = get_session_manager()

    async def _do():
        await sm.logout()
        return {"status": "logged out"}

    out.record(run(out, _do, label="session logout"), title="Logout")


@app.command()
def switch(
    ctx: typer.Context, account_id: str = typer.Argument(..., help="Target account ID.")
) -> None:
    """Switch the active account."""
    out = ctx.obj.out
    sm = get_session_manager()

    async def _do():
        await sm.ensure_logged_in()
        data = await sm.switch_account(account_id)
        data["active_account_id"] = sm.account_id
        return data

    out.record(run(out, _do, label="session switch"), title="Switch account")
