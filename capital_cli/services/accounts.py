"""AccountService — accounts, preferences, history, demo top-up.

Presentation-free: each method moves the request-building + HTTP call out of
``cli/account_cmds.py`` and returns the parsed JSON. No Typer/Rich/output here.

Mutation methods (``set_preferences``, ``demo_topup``) enforce their guard
*inside* the service, before any HTTP request, so SDK consumers are protected
exactly as the CLI is.
"""

from __future__ import annotations

from typing import Any

from capital_cli.core.config import get_config
from capital_cli.core.errors import ConfirmRequiredError
from capital_cli.core.http_client import get_client
from capital_cli.core.risk import get_risk_engine
from capital_cli.core.session import get_session_manager


class AccountService:
    async def list(self) -> dict[str, Any]:
        """List all trading accounts (annotated with the active account id)."""
        sm = get_session_manager()
        await sm.ensure_logged_in()
        client = get_client()
        data = (await client.get("/accounts")).json()
        return {**data, "active_account_id": sm.account_id}

    async def get_preferences(self) -> dict[str, Any]:
        """Get account preferences (hedging, leverage)."""
        await get_session_manager().ensure_logged_in()
        client = get_client()
        return (await client.get("/accounts/preferences")).json()

    async def set_preferences(
        self,
        *,
        hedging: bool | None = None,
        leverages: dict[str, int] | None = None,
        confirm: bool,
    ) -> dict[str, Any]:
        """Set account preferences: hedging mode and/or per-asset-class leverage.

        Risk-gated: the mutation guard runs BEFORE the PUT request.
        """
        await get_session_manager().ensure_logged_in()
        client = get_client()
        get_risk_engine().validate_mutation_guards(confirm=confirm)
        body: dict[str, Any] = {}
        if hedging is not None:
            body["hedgingMode"] = hedging
        if leverages:
            body["leverages"] = leverages
        return (await client.put("/accounts/preferences", json=body)).json()

    async def demo_topup(self, amount: float, *, confirm: bool) -> dict[str, Any]:
        """Top up the demo account balance (demo environment only).

        Guarded: the demo-env check and the explicit-confirm check run BEFORE
        the POST request.
        """
        config = get_config()
        if config.cap_env.value != "demo":
            raise ValueError("Demo top-up is only available with --demo / CAP_ENV=demo.")
        if config.cap_require_explicit_confirm and not confirm:
            raise ConfirmRequiredError()
        await get_session_manager().ensure_logged_in()
        client = get_client()
        return (await client.post("/accounts/topUp", json={"amount": amount})).json()

    async def history_activity(
        self,
        *,
        last_period: int = 600,
        from_date: str | None = None,
        to_date: str | None = None,
        detailed: bool = False,
        deal_id: str | None = None,
    ) -> dict[str, Any]:
        """Get account activity history."""
        await get_session_manager().ensure_logged_in()
        client = get_client()
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

    async def history_transactions(
        self,
        *,
        last_period: int = 600,
        type_: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> dict[str, Any]:
        """Get transaction history."""
        await get_session_manager().ensure_logged_in()
        client = get_client()
        params: dict[str, Any] = {"lastPeriod": last_period}
        if type_:
            params["type"] = type_
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        return (await client.get("/history/transactions", params=params)).json()
