"""Root Typer application: global options and sub-command wiring."""

from __future__ import annotations

from pathlib import Path

import typer

from capital_cli import __version__
from capital_cli.cli import (
    account_cmds,
    market_cmds,
    session_cmds,
    stream_cmds,
    trade_cmds,
    watchlist_cmds,
)
from capital_cli.cli.context import init_state

app = typer.Typer(
    no_args_is_help=True,
    add_completion=True,
    help="capctl — command-line client for the Capital.com Open API.",
    rich_markup_mode="rich",
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"capctl {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    json_output: bool = typer.Option(
        False, "--json", help="Emit raw JSON instead of tables."
    ),
    env_file: Path | None = typer.Option(
        None, "--env-file", help="Path to a .env credentials file."
    ),
    demo: bool = typer.Option(False, "--demo", help="Force the demo environment."),
    live: bool = typer.Option(False, "--live", help="Force the live environment."),
    account: str | None = typer.Option(
        None, "--account", "-a", help="Account ID to use for this invocation."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
    version: bool | None = typer.Option(
        None,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Global options applied to every subcommand."""
    if demo and live:
        raise typer.BadParameter("Use only one of --demo / --live.")
    env = "demo" if demo else "live" if live else None
    ctx.obj = init_state(
        json_mode=json_output,
        env_file=env_file,
        env=env,
        account=account,
        verbose=verbose,
    )


app.add_typer(session_cmds.app, name="session")
app.add_typer(market_cmds.app, name="market")
app.add_typer(account_cmds.app, name="account")
app.add_typer(trade_cmds.app, name="trade")
app.add_typer(watchlist_cmds.app, name="watchlist")
app.add_typer(stream_cmds.app, name="stream")


def run_cli() -> None:
    """Console-script entry point (see pyproject [project.scripts])."""
    app()
