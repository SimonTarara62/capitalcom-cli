"""MarketService — market data reads (search, details, prices, sentiment, navigation).

Presentation-free: each method moves the request-building + HTTP call out of
``cli/market_cmds.py`` and returns the parsed JSON. No Typer/Rich/output here.
"""

from __future__ import annotations

from typing import Any

from capital_cli.core.http_client import get_client
from capital_cli.core.session import get_session_manager


class MarketService:
    async def search(
        self,
        term: str | None = None,
        *,
        epics: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Search markets by term or EPICs (results truncated client-side to ``limit``)."""
        await get_session_manager().ensure_logged_in()
        client = get_client()
        params: dict[str, Any] = {}
        if term:
            params["searchTerm"] = term
        if epics:
            params["epics"] = epics
        data = (await client.get("/markets", params=params)).json()
        return {**data, "markets": data.get("markets", [])[:limit]}

    async def get(self, epic: str) -> dict[str, Any]:
        """Get full market details and dealing rules for an EPIC."""
        await get_session_manager().ensure_logged_in()
        client = get_client()
        return (await client.get(f"/markets/{epic}")).json()

    async def prices(
        self,
        epic: str,
        *,
        resolution: str = "MINUTE_15",
        max_candles: int = 200,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> dict[str, Any]:
        """Get historical OHLC prices for an EPIC."""
        await get_session_manager().ensure_logged_in()
        client = get_client()
        params: dict[str, Any] = {"resolution": resolution, "max": max_candles}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        return (await client.get(f"/prices/{epic}", params=params)).json()

    async def sentiment(self, market_ids: list[str]) -> dict[str, Any]:
        """Get client sentiment for one market (single-id path) or several (batch)."""
        await get_session_manager().ensure_logged_in()
        client = get_client()
        if len(market_ids) == 1:
            return (await client.get(f"/clientsentiment/{market_ids[0]}")).json()
        return (
            await client.get("/clientsentiment", params={"marketIds": ",".join(market_ids)})
        ).json()

    async def navigation_root(self) -> dict[str, Any]:
        """Get the root market-navigation tree."""
        await get_session_manager().ensure_logged_in()
        client = get_client()
        return (await client.get("/marketnavigation")).json()

    async def navigation_node(self, node_id: str, *, limit: int | None = None) -> dict[str, Any]:
        """Get child nodes/markets under a navigation node."""
        await get_session_manager().ensure_logged_in()
        client = get_client()
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        return (await client.get(f"/marketnavigation/{node_id}", params=params)).json()
