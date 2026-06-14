"""WatchlistService — list, get, create, add/remove market, delete watchlists.

Presentation-free: each method moves the request-building + HTTP call out of
``cli/watchlist_cmds.py`` and returns the parsed JSON. No Typer/Rich/output here.

Mutation methods (``create``, ``add_market``, ``remove_market``, ``delete``)
enforce their guard *inside* the service, before any HTTP request, so SDK
consumers are protected exactly as the CLI is (single source of truth).
"""

from __future__ import annotations

from typing import Any

from capital_cli.core.http_client import get_client
from capital_cli.core.risk import get_risk_engine
from capital_cli.core.session import get_session_manager


class WatchlistService:
    async def list(self) -> dict[str, Any]:
        """List all watchlists."""
        await get_session_manager().ensure_logged_in()
        client = get_client()
        return (await client.get("/watchlists")).json()

    async def get(self, watchlist_id: str) -> dict[str, Any]:
        """Get a watchlist and its markets."""
        await get_session_manager().ensure_logged_in()
        client = get_client()
        return (await client.get(f"/watchlists/{watchlist_id}")).json()

    async def create(self, name: str, *, confirm: bool) -> dict[str, Any]:
        """Create a new watchlist.

        Risk-gated: the mutation guard runs BEFORE the POST request.
        """
        await get_session_manager().ensure_logged_in()
        client = get_client()
        get_risk_engine().validate_mutation_guards(confirm=confirm)
        return (await client.post("/watchlists", json={"name": name})).json()

    async def add_market(self, watchlist_id: str, epic: str, *, confirm: bool) -> dict[str, Any]:
        """Add a market to a watchlist.

        Risk-gated: the mutation guard runs BEFORE the PUT request.
        """
        await get_session_manager().ensure_logged_in()
        client = get_client()
        get_risk_engine().validate_mutation_guards(confirm=confirm)
        return (await client.put(f"/watchlists/{watchlist_id}", json={"epic": epic})).json()

    async def remove_market(self, watchlist_id: str, epic: str, *, confirm: bool) -> dict[str, Any]:
        """Remove a market from a watchlist.

        Risk-gated: the mutation guard runs BEFORE the DELETE request.
        """
        await get_session_manager().ensure_logged_in()
        client = get_client()
        get_risk_engine().validate_mutation_guards(confirm=confirm)
        resp = await client.delete(f"/watchlists/{watchlist_id}/{epic}")
        return resp.json() if resp.text else {"status": "removed"}

    async def delete(self, watchlist_id: str, *, confirm: bool) -> dict[str, Any]:
        """Delete a watchlist.

        Risk-gated: the mutation guard runs BEFORE the DELETE request.
        """
        await get_session_manager().ensure_logged_in()
        client = get_client()
        get_risk_engine().validate_mutation_guards(confirm=confirm)
        resp = await client.delete(f"/watchlists/{watchlist_id}")
        return resp.json() if resp.text else {"status": "deleted"}
