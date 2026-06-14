"""TradingService — positions, orders, previews, and guarded broker mutations.

Presentation-free: each method moves the broker orchestration out of
``cli/trade_cmds.py`` and returns the parsed JSON / preview result. No
Typer/Rich/output here.

MOVE-NOT-REWRITE: every mutation reproduces the exact CLI sequence —
execution guards, the open-position-limit check (execute-position only),
preview lookup, broker-request build, the HTTP call with the same
``rate_limit_type``, ``increment_order_count``, the confirmation wait, the
``active_account_id`` annotation, and the ``audit_mutation`` call — MINUS the
presentation-only ``warn_if_live`` banner, which stays in the CLI command.

``audit_mutation`` moves INTO the service because the audit line is a
side-effect of the mutation: SDK consumers get the same audit logging the CLI
has, not just CLI users.
"""

from __future__ import annotations

from typing import Any

from capital_cli.core.audit import audit_mutation
from capital_cli.core.config import get_config
from capital_cli.core.http_client import get_client
from capital_cli.core.models import PreviewResult
from capital_cli.core.risk import get_risk_engine
from capital_cli.core.session import get_session_manager
from capital_cli.services.confirmations import (
    build_broker_request,
    mutation_status,
    wait_for_confirmation,
)


def _apply_limit(rows: list[Any], limit: int | None) -> list[Any]:
    """Return at most ``limit`` rows (all rows when ``limit`` is None)."""
    return rows if limit is None else rows[:limit]


class TradingService:
    # ----- Read-only -----

    async def list_positions(self, *, limit: int | None = None) -> dict[str, Any]:
        """List open positions (truncated client-side to ``limit`` when given)."""
        sm = get_session_manager()
        client = get_client()
        await sm.ensure_logged_in()
        data = (await client.get("/positions")).json()
        data["positions"] = _apply_limit(data.get("positions", []), limit)
        return data

    async def get_position(self, deal_id: str) -> dict[str, Any]:
        """Get a single position by deal ID."""
        sm = get_session_manager()
        client = get_client()
        await sm.ensure_logged_in()
        return (await client.get(f"/positions/{deal_id}")).json()

    async def list_orders(self, *, limit: int | None = None) -> dict[str, Any]:
        """List working orders (truncated client-side to ``limit`` when given)."""
        sm = get_session_manager()
        client = get_client()
        await sm.ensure_logged_in()
        data = (await client.get("/workingorders")).json()
        data["workingOrders"] = _apply_limit(data.get("workingOrders", []), limit)
        return data

    # ----- Preview (no side effects) -----

    async def preview_position(self, request: Any) -> PreviewResult:
        """Validate a position against risk policy (no trade). Delegates to risk engine."""
        sm = get_session_manager()
        risk = get_risk_engine()
        await sm.ensure_logged_in()
        return await risk.preview_position(request)

    async def preview_working_order(self, request: Any) -> PreviewResult:
        """Validate a working order against risk policy (no order). Delegates to risk engine."""
        sm = get_session_manager()
        risk = get_risk_engine()
        await sm.ensure_logged_in()
        return await risk.preview_working_order(request)

    # ----- Execute (side effects, guarded) -----

    async def execute_position(
        self, preview_id: str, *, confirm: bool, wait: bool = True, timeout_s: float = 15.0
    ) -> dict[str, Any]:
        """Execute a previewed position (SIDE EFFECT).

        Sequence: guard -> open-position-limit -> preview -> build -> POST
        /positions -> increment -> confirm -> audit.
        """
        sm = get_session_manager()
        client = get_client()
        risk = get_risk_engine()
        await sm.ensure_logged_in()
        risk.validate_execution_guards(confirm=confirm, preview_id=preview_id)
        # Enforce the max-open-positions safety limit (engine makes no HTTP calls).
        open_positions = (await client.get("/positions")).json().get("positions", [])
        risk.check_open_position_limit(len(open_positions))
        normalized = risk.get_preview(preview_id).normalized_request
        body = build_broker_request(normalized, include_order_fields=False)
        data = (await client.post("/positions", json=body, rate_limit_type="trading")).json()
        risk.increment_order_count()
        if wait and "dealReference" in data:
            data["confirmation"] = await wait_for_confirmation(
                data["dealReference"], timeout_s=timeout_s
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
            status=mutation_status(data),
        )
        return data

    async def execute_working_order(
        self, preview_id: str, *, confirm: bool, wait: bool = True, timeout_s: float = 15.0
    ) -> dict[str, Any]:
        """Execute a previewed working order (SIDE EFFECT).

        Sequence: guard -> preview -> build -> POST /workingorders -> increment
        -> confirm -> audit.
        """
        sm = get_session_manager()
        client = get_client()
        risk = get_risk_engine()
        await sm.ensure_logged_in()
        risk.validate_execution_guards(confirm=confirm, preview_id=preview_id)
        normalized = risk.get_preview(preview_id).normalized_request
        body = build_broker_request(normalized, include_order_fields=True)
        data = (
            await client.post("/workingorders", json=body, rate_limit_type="trading")
        ).json()
        risk.increment_order_count()
        if wait and "dealReference" in data:
            data["confirmation"] = await wait_for_confirmation(
                data["dealReference"], timeout_s=timeout_s
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
            status=mutation_status(data),
        )
        return data

    async def close_position(
        self, deal_id: str, *, confirm: bool, wait: bool = True, timeout_s: float = 15.0
    ) -> dict[str, Any]:
        """Close an open position (SIDE EFFECT).

        Sequence: guard -> DELETE /positions/{id} -> confirm -> audit.
        """
        sm = get_session_manager()
        client = get_client()
        risk = get_risk_engine()
        await sm.ensure_logged_in()
        risk.validate_execution_guards(confirm=confirm)
        data = (await client.delete(f"/positions/{deal_id}")).json()
        if wait and "dealReference" in data:
            data["confirmation"] = await wait_for_confirmation(
                data["dealReference"], timeout_s=timeout_s
            )
        data["active_account_id"] = sm.account_id
        audit_mutation(
            command="close",
            env=get_config().cap_env.value,
            account=sm.account_id,
            deal_reference=data.get("dealReference"),
            status=mutation_status(data),
        )
        return data

    async def cancel_order(
        self, deal_id: str, *, confirm: bool, wait: bool = True, timeout_s: float = 15.0
    ) -> dict[str, Any]:
        """Cancel a working order (SIDE EFFECT).

        Sequence: guard -> DELETE /workingorders/{id} -> confirm -> audit.
        """
        sm = get_session_manager()
        client = get_client()
        risk = get_risk_engine()
        await sm.ensure_logged_in()
        risk.validate_execution_guards(confirm=confirm)
        data = (await client.delete(f"/workingorders/{deal_id}")).json()
        if wait and "dealReference" in data:
            data["confirmation"] = await wait_for_confirmation(
                data["dealReference"], timeout_s=timeout_s
            )
        data["active_account_id"] = sm.account_id
        audit_mutation(
            command="cancel",
            env=get_config().cap_env.value,
            account=sm.account_id,
            deal_reference=data.get("dealReference"),
            status=mutation_status(data),
        )
        return data

    async def amend_position(
        self,
        deal_id: str,
        *,
        body: dict[str, Any],
        confirm: bool,
        wait: bool = True,
        timeout_s: float = 15.0,
    ) -> dict[str, Any]:
        """Amend the stop-loss / take-profit on an open position (SIDE EFFECT).

        The caller (CLI) builds and validates ``body``; this method runs the
        guard then PUT /positions/{id} -> confirm -> audit.
        """
        sm = get_session_manager()
        client = get_client()
        risk = get_risk_engine()
        await sm.ensure_logged_in()
        risk.validate_execution_guards(confirm=confirm)
        data = (await client.put(f"/positions/{deal_id}", json=body)).json()
        if wait and "dealReference" in data:
            data["confirmation"] = await wait_for_confirmation(
                data["dealReference"], timeout_s=timeout_s
            )
        data["active_account_id"] = sm.account_id
        audit_mutation(
            command="amend-position",
            env=get_config().cap_env.value,
            account=sm.account_id,
            deal_reference=data.get("dealReference"),
            status=mutation_status(data),
        )
        return data

    async def amend_order(
        self,
        deal_id: str,
        *,
        body: dict[str, Any],
        confirm: bool,
        wait: bool = True,
        timeout_s: float = 15.0,
    ) -> dict[str, Any]:
        """Amend a working order's level/expiry/stops-limits (SIDE EFFECT).

        The caller (CLI) builds and validates ``body``; this method runs the
        guard then PUT /workingorders/{id} -> confirm -> audit.
        """
        sm = get_session_manager()
        client = get_client()
        risk = get_risk_engine()
        await sm.ensure_logged_in()
        risk.validate_execution_guards(confirm=confirm)
        data = (await client.put(f"/workingorders/{deal_id}", json=body)).json()
        if wait and "dealReference" in data:
            data["confirmation"] = await wait_for_confirmation(
                data["dealReference"], timeout_s=timeout_s
            )
        data["active_account_id"] = sm.account_id
        audit_mutation(
            command="amend-order",
            env=get_config().cap_env.value,
            account=sm.account_id,
            deal_reference=data.get("dealReference"),
            status=mutation_status(data),
        )
        return data
