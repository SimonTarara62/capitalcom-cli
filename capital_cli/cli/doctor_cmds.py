"""capctl doctor — preflight / capability probe for humans and agents.

Reports the resolved environment, the trading-safety posture, the remaining
daily order budget, and whether the broker is reachable and the credentials
work — WITHOUT ever emitting a secret. Useful as the first thing a new user or
an agent runs to confirm the setup before placing any orders.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import typer

from capital_cli.core.config import get_config
from capital_cli.core.errors import CapitalCLIError
from capital_cli.core.http_client import get_client
from capital_cli.core.session import get_session_manager
from capital_cli.core.state import get_state_store


async def _probe() -> dict[str, Any]:
    """Build the doctor report. Never raises for credential/network failures —
    those are reported as ``*_ok: false`` flags instead."""
    config = get_config()
    today = datetime.now(timezone.utc).date().isoformat()
    used = get_state_store().get_order_count(today)
    remaining = max(config.cap_max_orders_per_day - used, 0)

    report: dict[str, Any] = {
        "env": config.cap_env.value,
        "allow_trading": config.cap_allow_trading,
        "allowed_epics": config.allowed_epics_list,
        "dry_run": config.cap_dry_run,
        "max_orders_per_day": config.cap_max_orders_per_day,
        "orders_used_today": used,
        "orders_remaining_today": remaining,
        "server_time_ok": False,
        "credentials_ok": False,
    }

    # Reachability: GET /time needs no auth.
    try:
        await get_client().get("/time")
        report["server_time_ok"] = True
    except Exception as exc:  # noqa: BLE001 - report, don't raise
        report["server_time_error"] = type(exc).__name__

    # Credentials: a successful login proves the keys work.
    try:
        sm = get_session_manager()
        await sm.ensure_logged_in()
        report["credentials_ok"] = True
        report["account_id"] = sm.account_id
    except CapitalCLIError as exc:
        report["credentials_error"] = exc.code
    except Exception as exc:  # noqa: BLE001 - report, don't raise
        report["credentials_error"] = type(exc).__name__

    return report


def doctor(ctx: typer.Context) -> None:
    """Check env, credentials, and trading status (no secrets in output).

    Run this first to confirm capctl is wired up correctly before trading.
    """
    out = ctx.obj.out

    try:
        report = asyncio.run(_probe())
    except CapitalCLIError as exc:
        # Config-level failure (e.g. missing credentials): surface via the normal
        # structured-error path and the mapped exit code.
        from capital_cli.cli.runner import EXIT_CODES

        out.error(exc.code, exc.message)
        raise typer.Exit(code=EXIT_CODES.get(exc.code, 1)) from exc

    if out.json_mode:
        out.json_line(report)
    else:
        out.record(report, title="capctl doctor")

    if not report["credentials_ok"] or not report["server_time_ok"]:
        raise typer.Exit(code=1)
