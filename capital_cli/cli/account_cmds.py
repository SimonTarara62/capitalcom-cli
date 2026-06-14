"""capctl account ... — accounts, preferences, history, demo top-up."""

from __future__ import annotations

from typing import Any

import typer

from capital_cli.cli.runner import run
from capital_cli.services.accounts import AccountService

app = typer.Typer(no_args_is_help=True, help="Accounts: list, preferences, history.")


@app.command("list")
def list_accounts(ctx: typer.Context) -> None:
    """List all trading accounts."""
    out = ctx.obj.out

    async def _do() -> dict[str, Any]:
        return await AccountService().list()

    data = run(out, _do, label="account list")
    if out.json_mode:
        out.raw(data)
    else:
        rows = [
            {
                "accountId": a.get("accountId"),
                "accountName": a.get("accountName"),
                "balance": (a.get("balance") or {}).get("balance"),
                "currency": a.get("currency"),
                "active": a.get("accountId") == data.get("active_account_id"),
            }
            for a in data.get("accounts", [])
        ]
        out.rows(
            rows,
            ["accountId", "accountName", "balance", "currency", "active"],
            title="Accounts",
        )


@app.command("prefs-get")
def prefs_get(ctx: typer.Context) -> None:
    """Get account preferences (hedging, leverage)."""
    out = ctx.obj.out

    async def _do() -> dict[str, Any]:
        return await AccountService().get_preferences()

    out.record(run(out, _do, label="account prefs-get"), title="Account preferences")


@app.command("prefs-set")
def prefs_set(
    ctx: typer.Context,
    hedging: bool | None = typer.Option(
        None, "--hedging/--no-hedging", help="Enable/disable hedging mode."
    ),
    leverage: list[str] | None = typer.Option(
        None,
        "--leverage",
        help="Per asset class, e.g. --leverage CRYPTOCURRENCIES=2 (repeatable). "
        "Asset classes: SHARES, CURRENCIES, INDICES, CRYPTOCURRENCIES, COMMODITIES.",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm this risk-gated change."),
) -> None:
    """Set account preferences: hedging mode and/or per-asset-class leverage (risk-gated)."""
    out = ctx.obj.out
    leverages: dict[str, int] = {}
    for item in leverage or []:
        if "=" not in item:
            raise typer.BadParameter(f"Leverage must be ASSET=VALUE, got: {item!r}")
        asset, _, value = item.partition("=")
        try:
            leverages[asset.strip().upper()] = int(value)
        except ValueError:
            raise typer.BadParameter(f"Leverage value must be an integer: {item!r}") from None
    if hedging is None and not leverages:
        raise typer.BadParameter("Provide --hedging/--no-hedging and/or --leverage.")

    async def _do() -> dict[str, Any]:
        return await AccountService().set_preferences(
            hedging=hedging, leverages=leverages, confirm=yes
        )

    out.record(run(out, _do, label="account prefs-set"), title="Updated preferences")


@app.command("history-activity")
def history_activity(
    ctx: typer.Context,
    last_period: int = typer.Option(600, "--last", help="Last N seconds (max 86400)."),
    from_date: str | None = typer.Option(None, "--from", help="Start ISO 8601."),
    to_date: str | None = typer.Option(None, "--to", help="End ISO 8601."),
    detailed: bool = typer.Option(False, "--detailed", help="Include full activity details."),
    deal_id: str | None = typer.Option(None, "--deal-id", help="Filter to a single deal ID."),
) -> None:
    """Get account activity history."""
    out = ctx.obj.out

    async def _do() -> dict[str, Any]:
        return await AccountService().history_activity(
            last_period=last_period,
            from_date=from_date,
            to_date=to_date,
            detailed=detailed,
            deal_id=deal_id,
        )

    out.raw(run(out, _do, label="account history-activity"))


@app.command("history-transactions")
def history_transactions(
    ctx: typer.Context,
    last_period: int = typer.Option(600, "--last", help="Last N seconds."),
    type_: str | None = typer.Option(None, "--type", help="Transaction type filter."),
    from_date: str | None = typer.Option(None, "--from", help="Start ISO 8601."),
    to_date: str | None = typer.Option(None, "--to", help="End ISO 8601."),
) -> None:
    """Get transaction history."""
    out = ctx.obj.out

    async def _do() -> dict[str, Any]:
        return await AccountService().history_transactions(
            last_period=last_period, type_=type_, from_date=from_date, to_date=to_date
        )

    out.raw(run(out, _do, label="account history-transactions"))


@app.command()
def topup(
    ctx: typer.Context,
    amount: float = typer.Argument(..., help="Amount to add to the demo balance."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm the top-up."),
) -> None:
    """Top up the demo account balance (demo environment only)."""
    out = ctx.obj.out

    async def _do() -> dict[str, Any]:
        return await AccountService().demo_topup(amount, confirm=yes)

    out.record(run(out, _do, label="account topup"), title="Demo top-up")
