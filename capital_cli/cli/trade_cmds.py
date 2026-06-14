"""capctl trade ... — positions, orders, confirmations, preview, execute."""

from __future__ import annotations

from typing import Any

import typer

from capital_cli.cli.live_guard import warn_if_live
from capital_cli.cli.runner import run
from capital_cli.core.audit import audit_mutation
from capital_cli.core.config import get_config
from capital_cli.core.http_client import get_client
from capital_cli.core.models import (
    Direction,
    PreviewPositionRequest,
    PreviewWorkingOrderRequest,
    WorkingOrderType,
)
from capital_cli.core.risk import get_risk_engine
from capital_cli.core.session import get_session_manager
from capital_cli.core.utils import poll_until

app = typer.Typer(no_args_is_help=True, help="Trading: positions, orders, preview, execute.")


async def _wait_for_confirmation(
    deal_reference: str, timeout_s: float, poll_interval_ms: int = 500
) -> dict[str, Any]:
    """Poll GET /confirms/{dealReference} until the broker accepts or rejects the deal.

    The Capital.com API reports the broker's decision in the ``dealStatus``
    field (ACCEPTED/REJECTED); ``status`` is the resulting position/order
    lifecycle state (e.g. OPEN, CLOSED) and is not a useful done-condition.
    The returned dict normalizes ``status`` to the ``dealStatus`` value so
    callers can uniformly check ``confirmation["status"]``.
    """
    client = get_client()

    async def check() -> dict[str, Any]:
        return (await client.get(f"/confirms/{deal_reference}")).json()

    def done(data: dict[str, Any]) -> bool:
        return data.get("dealStatus") in ("ACCEPTED", "REJECTED")

    result = await poll_until(check, done, timeout_s=timeout_s, poll_interval_ms=poll_interval_ms)
    if result is None:
        return {
            "status": "TIMEOUT",
            "message": f"Confirmation timed out after {timeout_s}s",
        }
    if "dealStatus" in result:
        result = {**result, "status": result["dealStatus"]}
    return result


def _mutation_status(data: dict[str, Any]) -> str:
    """Derive an audit status string from a broker mutation response.

    Prefers the confirmation's normalized ``status`` (ACCEPTED/REJECTED/TIMEOUT),
    then a top-level ``dealStatus``, then ``status``, else ``SUBMITTED``.
    """
    confirmation = data.get("confirmation")
    if isinstance(confirmation, dict) and confirmation.get("status"):
        return str(confirmation["status"])
    if data.get("dealStatus"):
        return str(data["dealStatus"])
    if data.get("status"):
        return str(data["status"])
    return "SUBMITTED"


def _parse_direction(direction: str) -> Direction:
    try:
        return Direction(direction.upper())
    except ValueError:
        raise typer.BadParameter("direction must be BUY or SELL.") from None


def _parse_order_type(order_type: str) -> WorkingOrderType:
    try:
        return WorkingOrderType(order_type.upper())
    except ValueError:
        raise typer.BadParameter("order type must be LIMIT or STOP.") from None


def _preview_payload(preview: Any) -> dict[str, Any]:
    return {
        "preview_id": preview.preview_id,
        "normalized_request": preview.normalized_request,
        "checks": [c.model_dump() for c in preview.checks],
        "all_checks_passed": preview.all_checks_passed,
        "estimated_entry": preview.estimated_entry,
        "estimated_risk_notes": preview.estimated_risk_notes,
        "expires_in_seconds": 120,
    }


# ----- Read-only -----


@app.command(
    epilog=(
        "Examples:\n"
        "  # List open positions as JSON and sum unrealised P&L with jq\n"
        "  capctl --json trade positions | jq '[.positions[].position.upl] | add'"
    )
)
def positions(ctx: typer.Context) -> None:
    """List open positions."""
    out = ctx.obj.out

    async def _do() -> dict[str, Any]:
        sm = get_session_manager()
        client = get_client()
        await sm.ensure_logged_in()
        return (await client.get("/positions")).json()

    data = run(out, _do, label="trade positions")
    if out.json_mode:
        out.raw(data)
    else:
        rows = [
            {
                "dealId": p.get("position", {}).get("dealId"),
                "epic": p.get("market", {}).get("epic"),
                "direction": p.get("position", {}).get("direction"),
                "size": p.get("position", {}).get("size"),
                "level": p.get("position", {}).get("level"),
                "upl": p.get("position", {}).get("upl"),
            }
            for p in data.get("positions", [])
        ]
        out.rows(
            rows,
            ["dealId", "epic", "direction", "size", "level", "upl"],
            title="Open positions",
        )


@app.command()
def position(
    ctx: typer.Context, deal_id: str = typer.Argument(..., help="Position deal ID.")
) -> None:
    """Get a single position by deal ID."""
    out = ctx.obj.out

    async def _do() -> dict[str, Any]:
        sm = get_session_manager()
        client = get_client()
        await sm.ensure_logged_in()
        return (await client.get(f"/positions/{deal_id}")).json()

    out.raw(run(out, _do, label="trade position"))


@app.command()
def orders(ctx: typer.Context) -> None:
    """List working orders."""
    out = ctx.obj.out

    async def _do() -> dict[str, Any]:
        sm = get_session_manager()
        client = get_client()
        await sm.ensure_logged_in()
        return (await client.get("/workingorders")).json()

    data = run(out, _do, label="trade orders")
    if out.json_mode:
        out.raw(data)
    else:
        rows = [
            {
                "dealId": o.get("workingOrderData", {}).get("dealId"),
                "epic": o.get("marketData", {}).get("epic"),
                "direction": o.get("workingOrderData", {}).get("direction"),
                "type": o.get("workingOrderData", {}).get("orderType"),
                "level": o.get("workingOrderData", {}).get("orderLevel"),
                "size": o.get("workingOrderData", {}).get("orderSize"),
            }
            for o in data.get("workingOrders", [])
        ]
        out.rows(
            rows,
            ["dealId", "epic", "direction", "type", "level", "size"],
            title="Working orders",
        )


@app.command()
def confirm(
    ctx: typer.Context,
    deal_reference: str = typer.Argument(..., help="Deal reference (e.g. o_...)."),
    wait: bool = typer.Option(False, "--wait", help="Poll until ACCEPTED/REJECTED."),
    timeout: float = typer.Option(15.0, "--timeout", help="Polling timeout in seconds."),
) -> None:
    """Get (or wait for) a deal confirmation."""
    out = ctx.obj.out

    async def _do() -> dict[str, Any]:
        sm = get_session_manager()
        client = get_client()
        await sm.ensure_logged_in()
        if wait:
            return await _wait_for_confirmation(deal_reference, timeout_s=timeout)
        return (await client.get(f"/confirms/{deal_reference}")).json()

    out.record(run(out, _do, label="trade confirm"), title="Confirmation")


# ----- Preview (no side effects) -----


@app.command(
    "preview-position",
    epilog=(
        "Examples:\n"
        "  # 1) Preview, capturing the preview_id\n"
        "  PV=$(capctl --json trade preview-position GOLD BUY 1 | jq -r .preview_id)\n"
        "  # 2) Execute that preview (requires --yes)\n"
        '  capctl --json trade execute-position "$PV" --yes'
    ),
)
def preview_position(
    ctx: typer.Context,
    epic: str = typer.Argument(..., help="Market EPIC."),
    direction: str = typer.Argument(..., help="BUY or SELL."),
    size: float = typer.Argument(..., help="Position size."),
    stop_level: float | None = typer.Option(None, "--stop-level"),
    stop_distance: float | None = typer.Option(None, "--stop-distance"),
    profit_level: float | None = typer.Option(None, "--profit-level"),
    profit_distance: float | None = typer.Option(None, "--profit-distance"),
    guaranteed_stop: bool = typer.Option(False, "--guaranteed-stop"),
    trailing_stop: bool = typer.Option(False, "--trailing-stop"),
    auto_normalize_size: bool = typer.Option(
        False,
        "--auto-normalize-size",
        help="Round size to the broker increment instead of failing.",
    ),
) -> None:
    """Validate a position against risk policy and return a preview_id (no trade)."""
    out = ctx.obj.out
    direction_e = _parse_direction(direction)

    async def _do() -> dict[str, Any]:
        warn_if_live(out)
        sm = get_session_manager()
        risk = get_risk_engine()
        await sm.ensure_logged_in()
        request = PreviewPositionRequest(
            epic=epic,
            direction=direction_e,
            size=size,
            guaranteed_stop=guaranteed_stop,
            trailing_stop=trailing_stop,
            stop_level=stop_level,
            stop_distance=stop_distance,
            profit_level=profit_level,
            profit_distance=profit_distance,
            auto_normalize_size=auto_normalize_size,
        )
        return _preview_payload(await risk.preview_position(request))

    data = run(out, _do, label="trade preview-position")
    if out.json_mode:
        out.raw(data)
    else:
        out.rows(data["checks"], ["check", "passed", "message"], title="Risk checks")
        out.record(
            {
                "preview_id": data["preview_id"],
                "all_checks_passed": data["all_checks_passed"],
                "estimated_entry": data["estimated_entry"],
                "expires_in_seconds": data["expires_in_seconds"],
            },
            title="Preview",
        )


@app.command(
    "preview-order",
    epilog=(
        "Examples:\n"
        "  # 1) Preview a LIMIT working order, capturing the preview_id\n"
        "  PV=$(capctl --json trade preview-order GOLD BUY LIMIT 1900 1 | jq -r .preview_id)\n"
        "  # 2) Execute that preview (requires --yes)\n"
        '  capctl --json trade execute-order "$PV" --yes'
    ),
)
def preview_order(
    ctx: typer.Context,
    epic: str = typer.Argument(..., help="Market EPIC."),
    direction: str = typer.Argument(..., help="BUY or SELL."),
    order_type: str = typer.Argument(..., help="LIMIT or STOP."),
    level: float = typer.Argument(..., help="Trigger level."),
    size: float = typer.Argument(..., help="Order size."),
    stop_level: float | None = typer.Option(None, "--stop-level"),
    profit_level: float | None = typer.Option(None, "--profit-level"),
    good_till_date: str | None = typer.Option(None, "--good-till", help="Expiry ISO 8601."),
    auto_normalize_size: bool = typer.Option(
        False,
        "--auto-normalize-size",
        help="Round size to the broker increment instead of failing.",
    ),
) -> None:
    """Validate a working order and return a preview_id (no order created)."""
    out = ctx.obj.out
    direction_e = _parse_direction(direction)
    order_type_e = _parse_order_type(order_type)

    async def _do() -> dict[str, Any]:
        warn_if_live(out)
        sm = get_session_manager()
        risk = get_risk_engine()
        await sm.ensure_logged_in()
        request = PreviewWorkingOrderRequest(
            epic=epic,
            direction=direction_e,
            type=order_type_e,
            level=level,
            size=size,
            stop_level=stop_level,
            profit_level=profit_level,
            good_till_date=good_till_date,
            auto_normalize_size=auto_normalize_size,
        )
        return _preview_payload(await risk.preview_working_order(request))

    data = run(out, _do, label="trade preview-order")
    if out.json_mode:
        out.raw(data)
    else:
        out.rows(data["checks"], ["check", "passed", "message"], title="Risk checks")
        out.record(
            {"preview_id": data["preview_id"], "all_checks_passed": data["all_checks_passed"]},
            title="Preview",
        )


# ----- Execute (side effects, guarded) -----


def _build_broker_request(
    normalized: dict[str, Any], *, include_order_fields: bool
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "epic": normalized["epic"],
        "direction": normalized["direction"],
        "size": normalized["size"],
    }
    if include_order_fields:
        body["type"] = normalized["type"]
        body["level"] = normalized["level"]
        if normalized.get("good_till_date"):
            body["goodTillDate"] = normalized["good_till_date"]
    if normalized.get("guaranteed_stop"):
        body["guaranteedStop"] = True
    if normalized.get("trailing_stop"):
        body["trailingStop"] = True
    for src, dst in [
        ("stop_level", "stopLevel"),
        ("stop_distance", "stopDistance"),
        ("stop_amount", "stopAmount"),
        ("profit_level", "profitLevel"),
        ("profit_distance", "profitDistance"),
        ("profit_amount", "profitAmount"),
    ]:
        if normalized.get(src):
            body[dst] = normalized[src]
    return body


@app.command(
    "execute-position",
    epilog=(
        "Examples:\n"
        "  # Execute a previewed position; a TIMEOUT confirmation is ambiguous —\n"
        "  # reconcile with 'trade positions' before retrying.\n"
        '  capctl --json trade execute-position "$PREVIEW_ID" --yes'
    ),
)
def execute_position(
    ctx: typer.Context,
    preview_id: str = typer.Argument(..., help="Preview ID from preview-position."),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Confirm execution (creates a real trade)."
    ),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Wait for broker confirmation."),
    timeout: float = typer.Option(15.0, "--timeout"),
) -> None:
    """Execute a previewed position (SIDE EFFECT)."""
    out = ctx.obj.out

    async def _do() -> dict[str, Any]:
        warn_if_live(out)
        sm = get_session_manager()
        client = get_client()
        risk = get_risk_engine()
        await sm.ensure_logged_in()
        risk.validate_execution_guards(confirm=yes, preview_id=preview_id)
        # Enforce the max-open-positions safety limit (engine makes no HTTP calls).
        open_positions = (await client.get("/positions")).json().get("positions", [])
        risk.check_open_position_limit(len(open_positions))
        normalized = risk.get_preview(preview_id).normalized_request
        body = _build_broker_request(normalized, include_order_fields=False)
        data = (await client.post("/positions", json=body, rate_limit_type="trading")).json()
        risk.increment_order_count()
        if wait and "dealReference" in data:
            data["confirmation"] = await _wait_for_confirmation(
                data["dealReference"], timeout_s=timeout
            )
        data["active_account_id"] = sm.account_id
        audit_mutation(
            command="execute-position",
            env=get_config().cap_env.value,
            account=sm.account_id,
            epic=normalized.get("epic"),
            size=normalized.get("size"),
            preview_id=preview_id,
            deal_reference=data.get("dealReference"),
            status=_mutation_status(data),
        )
        return data

    out.record(run(out, _do, label="trade execute-position"), title="Execute position")


@app.command(
    "execute-order",
    epilog=(
        "Examples:\n"
        "  # Execute a previewed working order; reconcile via 'trade orders' on TIMEOUT.\n"
        '  capctl --json trade execute-order "$PREVIEW_ID" --yes'
    ),
)
def execute_order(
    ctx: typer.Context,
    preview_id: str = typer.Argument(..., help="Preview ID from preview-order."),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Confirm execution (creates a real order)."
    ),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Wait for broker confirmation."),
    timeout: float = typer.Option(15.0, "--timeout"),
) -> None:
    """Execute a previewed working order (SIDE EFFECT)."""
    out = ctx.obj.out

    async def _do() -> dict[str, Any]:
        warn_if_live(out)
        sm = get_session_manager()
        client = get_client()
        risk = get_risk_engine()
        await sm.ensure_logged_in()
        risk.validate_execution_guards(confirm=yes, preview_id=preview_id)
        normalized = risk.get_preview(preview_id).normalized_request
        body = _build_broker_request(normalized, include_order_fields=True)
        data = (await client.post("/workingorders", json=body, rate_limit_type="trading")).json()
        risk.increment_order_count()
        if wait and "dealReference" in data:
            data["confirmation"] = await _wait_for_confirmation(
                data["dealReference"], timeout_s=timeout
            )
        data["active_account_id"] = sm.account_id
        audit_mutation(
            command="execute-order",
            env=get_config().cap_env.value,
            account=sm.account_id,
            epic=normalized.get("epic"),
            size=normalized.get("size"),
            preview_id=preview_id,
            deal_reference=data.get("dealReference"),
            status=_mutation_status(data),
        )
        return data

    out.record(run(out, _do, label="trade execute-order"), title="Execute order")


@app.command(
    epilog=(
        "Examples:\n"
        "  # Close a position by deal ID (requires --yes)\n"
        "  capctl --json trade close DIAAAAA... --yes"
    )
)
def close(
    ctx: typer.Context,
    deal_id: str = typer.Argument(..., help="Position deal ID to close."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm closing the position."),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Wait for broker confirmation."),
    timeout: float = typer.Option(15.0, "--timeout"),
) -> None:
    """Close an open position (SIDE EFFECT)."""
    out = ctx.obj.out

    async def _do() -> dict[str, Any]:
        warn_if_live(out)
        sm = get_session_manager()
        client = get_client()
        risk = get_risk_engine()
        await sm.ensure_logged_in()
        risk.validate_execution_guards(confirm=yes)
        data = (await client.delete(f"/positions/{deal_id}")).json()
        if wait and "dealReference" in data:
            data["confirmation"] = await _wait_for_confirmation(
                data["dealReference"], timeout_s=timeout
            )
        data["active_account_id"] = sm.account_id
        audit_mutation(
            command="close",
            env=get_config().cap_env.value,
            account=sm.account_id,
            deal_reference=data.get("dealReference"),
            status=_mutation_status(data),
        )
        return data

    out.record(run(out, _do, label="trade close"), title="Close position")


@app.command()
def cancel(
    ctx: typer.Context,
    deal_id: str = typer.Argument(..., help="Working order deal ID to cancel."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm cancelling the order."),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Wait for broker confirmation."),
    timeout: float = typer.Option(15.0, "--timeout"),
) -> None:
    """Cancel a working order (SIDE EFFECT)."""
    out = ctx.obj.out

    async def _do() -> dict[str, Any]:
        warn_if_live(out)
        sm = get_session_manager()
        client = get_client()
        risk = get_risk_engine()
        await sm.ensure_logged_in()
        risk.validate_execution_guards(confirm=yes)
        data = (await client.delete(f"/workingorders/{deal_id}")).json()
        if wait and "dealReference" in data:
            data["confirmation"] = await _wait_for_confirmation(
                data["dealReference"], timeout_s=timeout
            )
        data["active_account_id"] = sm.account_id
        audit_mutation(
            command="cancel",
            env=get_config().cap_env.value,
            account=sm.account_id,
            deal_reference=data.get("dealReference"),
            status=_mutation_status(data),
        )
        return data

    out.record(run(out, _do, label="trade cancel"), title="Cancel order")


@app.command("amend-position")
def amend_position(
    ctx: typer.Context,
    deal_id: str = typer.Argument(..., help="Deal ID of the open position to amend."),
    stop_level: float | None = typer.Option(None, "--stop-level"),
    stop_distance: float | None = typer.Option(None, "--stop-distance"),
    profit_level: float | None = typer.Option(None, "--profit-level"),
    profit_distance: float | None = typer.Option(None, "--profit-distance"),
    guaranteed_stop: bool | None = typer.Option(
        None, "--guaranteed-stop/--no-guaranteed-stop", help="Toggle guaranteed stop."
    ),
    trailing_stop: bool | None = typer.Option(
        None, "--trailing-stop/--no-trailing-stop", help="Toggle trailing stop."
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm the amendment."),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Wait for broker confirmation."),
    timeout: float = typer.Option(15.0, "--timeout"),
) -> None:
    """Amend the stop-loss / take-profit on an open position (SIDE EFFECT)."""
    out = ctx.obj.out
    body: dict[str, Any] = {}
    for value, key in [
        (stop_level, "stopLevel"),
        (stop_distance, "stopDistance"),
        (profit_level, "profitLevel"),
        (profit_distance, "profitDistance"),
    ]:
        if value is not None:
            body[key] = value
    if guaranteed_stop is not None:
        body["guaranteedStop"] = guaranteed_stop
    if trailing_stop is not None:
        body["trailingStop"] = trailing_stop
    if not body:
        raise typer.BadParameter("Provide at least one stop/profit option to amend.")

    async def _do() -> dict[str, Any]:
        warn_if_live(out)
        sm = get_session_manager()
        client = get_client()
        risk = get_risk_engine()
        await sm.ensure_logged_in()
        risk.validate_execution_guards(confirm=yes)
        data = (await client.put(f"/positions/{deal_id}", json=body)).json()
        if wait and "dealReference" in data:
            data["confirmation"] = await _wait_for_confirmation(
                data["dealReference"], timeout_s=timeout
            )
        data["active_account_id"] = sm.account_id
        audit_mutation(
            command="amend-position",
            env=get_config().cap_env.value,
            account=sm.account_id,
            deal_reference=data.get("dealReference"),
            status=_mutation_status(data),
        )
        return data

    out.record(run(out, _do, label="trade amend-position"), title="Amend position")


@app.command("amend-order")
def amend_order(
    ctx: typer.Context,
    deal_id: str = typer.Argument(..., help="Deal ID of the working order to amend."),
    level: float | None = typer.Option(None, "--level", help="New trigger level."),
    good_till_date: str | None = typer.Option(None, "--good-till", help="New expiry ISO 8601."),
    stop_level: float | None = typer.Option(None, "--stop-level"),
    stop_distance: float | None = typer.Option(None, "--stop-distance"),
    profit_level: float | None = typer.Option(None, "--profit-level"),
    profit_distance: float | None = typer.Option(None, "--profit-distance"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm the amendment."),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Wait for broker confirmation."),
    timeout: float = typer.Option(15.0, "--timeout"),
) -> None:
    """Amend a working order's level, expiry, or stops/limits (SIDE EFFECT)."""
    out = ctx.obj.out
    body: dict[str, Any] = {}
    if level is not None:
        body["level"] = level
    if good_till_date is not None:
        body["goodTillDate"] = good_till_date
    for value, key in [
        (stop_level, "stopLevel"),
        (stop_distance, "stopDistance"),
        (profit_level, "profitLevel"),
        (profit_distance, "profitDistance"),
    ]:
        if value is not None:
            body[key] = value
    if not body:
        raise typer.BadParameter(
            "Provide at least one field to amend (level, good-till, stop/profit)."
        )

    async def _do() -> dict[str, Any]:
        warn_if_live(out)
        sm = get_session_manager()
        client = get_client()
        risk = get_risk_engine()
        await sm.ensure_logged_in()
        risk.validate_execution_guards(confirm=yes)
        data = (await client.put(f"/workingorders/{deal_id}", json=body)).json()
        if wait and "dealReference" in data:
            data["confirmation"] = await _wait_for_confirmation(
                data["dealReference"], timeout_s=timeout
            )
        data["active_account_id"] = sm.account_id
        audit_mutation(
            command="amend-order",
            env=get_config().cap_env.value,
            account=sm.account_id,
            deal_reference=data.get("dealReference"),
            status=_mutation_status(data),
        )
        return data

    out.record(run(out, _do, label="trade amend-order"), title="Amend order")
