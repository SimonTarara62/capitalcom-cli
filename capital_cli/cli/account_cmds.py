"""capctl account ... — accounts, preferences, history, demo top-up."""

from __future__ import annotations

from typing import Any

import typer

from capital_cli.cli.runner import run
from capital_cli.core.config import get_config
from capital_cli.core.errors import ConfirmRequiredError
from capital_cli.core.http_client import get_client
from capital_cli.core.risk import get_risk_engine
from capital_cli.core.session import get_session_manager

app = typer.Typer(no_args_is_help=True, help="Accounts: list, preferences, history.")


@app.command("list")
def list_accounts(ctx: typer.Context) -> None:
    """List all trading accounts."""
    out = ctx.obj.out
    sm = get_session_manager()
    client = get_client()

    async def _do() -> dict[str, Any]:
        await sm.ensure_logged_in()
        data = (await client.get("/accounts")).json()
        data["active_account_id"] = sm.account_id
        return data

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
    sm = get_session_manager()
    client = get_client()

    async def _do() -> dict[str, Any]:
        await sm.ensure_logged_in()
        return (await client.get("/accounts/preferences")).json()

    out.record(run(out, _do, label="account prefs-get"), title="Account preferences")


@app.command("prefs-set")
def prefs_set(
    ctx: typer.Context,
    hedging: bool | None = typer.Option(
        None, "--hedging/--no-hedging", help="Enable/disable hedging mode."
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm this risk-gated change."),
) -> None:
    """Set account preferences (risk-gated: requires trading enabled + --yes)."""
    out = ctx.obj.out
    sm = get_session_manager()
    client = get_client()
    risk = get_risk_engine()

    async def _do() -> dict[str, Any]:
        await sm.ensure_logged_in()
        risk.validate_execution_guards(confirm=yes)
        body: dict[str, Any] = {}
        if hedging is not None:
            body["hedgingMode"] = hedging
        return (await client.put("/accounts/preferences", json=body)).json()

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
    sm = get_session_manager()
    client = get_client()

    async def _do() -> dict[str, Any]:
        await sm.ensure_logged_in()
        params: dict[str, Any] = {"lastPeriod": last_period}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        if detailed:
            params["detailed"] = "true"
        if deal_id:
            params["dealId"] = deal_id
        return (await client.get("/history/activity", params=params)).json()

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
    sm = get_session_manager()
    client = get_client()

    async def _do() -> dict[str, Any]:
        await sm.ensure_logged_in()
        params: dict[str, Any] = {"lastPeriod": last_period}
        if type_:
            params["type"] = type_
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        return (await client.get("/history/transactions", params=params)).json()

    out.raw(run(out, _do, label="account history-transactions"))


@app.command()
def topup(
    ctx: typer.Context,
    amount: float = typer.Argument(..., help="Amount to add to the demo balance."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm the top-up."),
) -> None:
    """Top up the demo account balance (demo environment only)."""
    out = ctx.obj.out
    sm = get_session_manager()
    client = get_client()
    config = get_config()

    async def _do() -> dict[str, Any]:
        if config.cap_env.value != "demo":
            raise typer.BadParameter("Demo top-up is only available with --demo / CAP_ENV=demo.")
        if config.cap_require_explicit_confirm and not yes:
            raise ConfirmRequiredError()
        await sm.ensure_logged_in()
        return (await client.post("/accounts/topUp", json={"amount": amount})).json()

    out.record(run(out, _do, label="account topup"), title="Demo top-up")
