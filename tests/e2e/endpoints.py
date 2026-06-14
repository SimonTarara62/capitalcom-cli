"""Canonical Capital.com Open API endpoint registry — the single source of truth
for the coverage matrix. `docs/api-coverage.md` and the README coverage badge are
GENERATED from this file (see tools/render_coverage.py). Do not hand-edit the
generated table; edit this registry and re-render.

Cross-check basis: the official Capital.com Open API REST + streaming surface
(https://open-api.capital.com/) and the sibling capital-com MCP server, which
mirrors that surface. `OFFICIAL_SURFACE` below is that published set; the
completeness test asserts the registry matches it exactly.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Endpoint:
    id: str
    http: str          # REST verb+path or WS destination, or "(local)" for risk-engine ops
    cli: str           # CLI command path
    sdk: str | None    # SDK method dotted path, or None if not exposed on the SDK (N/A)
    category: str      # session | account | market | position | order | trade | watchlist | stream
    mutating: bool


# --- The 41-row registry (mirror of docs/api-coverage.md row order) ----------
ENDPOINTS: list[Endpoint] = [
    Endpoint("session.time", "GET /time", "session time", None, "session", False),
    Endpoint("session.ping", "GET /ping", "session ping", "session.ping", "session", False),
    Endpoint("session.details", "GET /session", "session details", None, "session", False),
    Endpoint("session.encryption_key", "GET /session/encryptionKey", "session encryption-key", None, "session", False),
    Endpoint("session.login", "POST /session", "session login", "session.login", "session", True),
    Endpoint("session.switch", "PUT /session", "session switch", "session.switch_account", "session", True),
    Endpoint("session.logout", "DELETE /session", "session logout", "session.logout", "session", True),
    Endpoint("account.list", "GET /accounts", "account list", "accounts.list", "account", False),
    Endpoint("account.prefs_get", "GET /accounts/preferences", "account prefs-get", "accounts.get_preferences", "account", False),
    Endpoint("account.prefs_set", "PUT /accounts/preferences", "account prefs-set", "accounts.set_preferences", "account", True),
    Endpoint("account.history_activity", "GET /history/activity", "account history-activity", "accounts.history_activity", "account", False),
    Endpoint("account.history_transactions", "GET /history/transactions", "account history-transactions", "accounts.history_transactions", "account", False),
    Endpoint("account.topup", "POST /accounts/topUp", "account topup", "accounts.demo_topup", "account", True),
    Endpoint("market.search", "GET /markets", "market search", "markets.search", "market", False),
    Endpoint("market.get", "GET /markets/{epic}", "market get", "markets.get", "market", False),
    Endpoint("market.nav_root", "GET /marketnavigation", "market nav-root", "markets.navigation_root", "market", False),
    Endpoint("market.nav_node", "GET /marketnavigation/{id}", "market nav-node", "markets.navigation_node", "market", False),
    Endpoint("market.prices", "GET /prices/{epic}", "market prices", "markets.prices", "market", False),
    Endpoint("market.sentiment", "GET /clientsentiment", "market sentiment", "markets.sentiment", "market", False),
    Endpoint("position.list", "GET /positions", "trade positions", "trading.list_positions", "position", False),
    Endpoint("position.get", "GET /positions/{dealId}", "trade position", "trading.get_position", "position", False),
    Endpoint("position.preview", "(local)", "trade preview-position", "trading.preview_position", "position", False),
    Endpoint("position.execute", "POST /positions", "trade execute-position", "trading.execute_position", "position", True),
    Endpoint("position.amend", "PUT /positions/{dealId}", "trade amend-position", "trading.amend_position", "position", True),
    Endpoint("position.close", "DELETE /positions/{dealId}", "trade close", "trading.close_position", "position", True),
    Endpoint("order.list", "GET /workingorders", "trade orders", "trading.list_orders", "order", False),
    Endpoint("order.preview", "(local)", "trade preview-order", "trading.preview_working_order", "order", False),
    Endpoint("order.execute", "POST /workingorders", "trade execute-order", "trading.execute_working_order", "order", True),
    Endpoint("order.amend", "PUT /workingorders/{dealId}", "trade amend-order", "trading.amend_order", "order", True),
    Endpoint("order.cancel", "DELETE /workingorders/{dealId}", "trade cancel", "trading.cancel_order", "order", True),
    Endpoint("trade.confirm", "GET /confirms/{dealRef}", "trade confirm", "confirmations.get_confirmation", "trade", False),
    Endpoint("watchlist.list", "GET /watchlists", "watchlist list", "watchlists.list", "watchlist", False),
    Endpoint("watchlist.create", "POST /watchlists", "watchlist create", "watchlists.create", "watchlist", True),
    Endpoint("watchlist.get", "GET /watchlists/{id}", "watchlist get", "watchlists.get", "watchlist", False),
    Endpoint("watchlist.add", "PUT /watchlists/{id}", "watchlist add", "watchlists.add_market", "watchlist", True),
    Endpoint("watchlist.remove", "DELETE /watchlists/{id}/{epic}", "watchlist remove", "watchlists.remove_market", "watchlist", True),
    Endpoint("watchlist.delete", "DELETE /watchlists/{id}", "watchlist delete", "watchlists.delete", "watchlist", True),
    Endpoint("stream.prices", "WS marketData.subscribe", "stream prices", "stream.prices", "stream", False),
    Endpoint("stream.candles", "WS OHLCMarketData.subscribe", "stream candles", "stream.candles", "stream", False),
    Endpoint("stream.alerts", "WS quotes (level cross)", "stream alerts", "stream.alerts", "stream", False),
    Endpoint("stream.portfolio", "WS quotes (position epics)", "stream portfolio", "stream.portfolio", "stream", False),
]

# The published Capital.com Open API surface: every REST endpoint + WS destination
# the registry claims to cover, authored INDEPENDENTLY of ENDPOINTS so the
# cross-check (test_registry_matches_official_surface) actually catches drift —
# an endpoint added to/removed from one list but not the other fails the test.
# Excludes the two "(local)" preview operations (client-side risk-engine, not API
# calls). Update this set ONLY when Capital.com publishes/removes an endpoint.
OFFICIAL_SURFACE: set[str] = {
    # session
    "GET /time",
    "GET /ping",
    "GET /session",
    "GET /session/encryptionKey",
    "POST /session",
    "PUT /session",
    "DELETE /session",
    # account
    "GET /accounts",
    "GET /accounts/preferences",
    "PUT /accounts/preferences",
    "GET /history/activity",
    "GET /history/transactions",
    "POST /accounts/topUp",
    # market
    "GET /markets",
    "GET /markets/{epic}",
    "GET /marketnavigation",
    "GET /marketnavigation/{id}",
    "GET /prices/{epic}",
    "GET /clientsentiment",
    # positions
    "GET /positions",
    "GET /positions/{dealId}",
    "POST /positions",
    "PUT /positions/{dealId}",
    "DELETE /positions/{dealId}",
    # working orders
    "GET /workingorders",
    "POST /workingorders",
    "PUT /workingorders/{dealId}",
    "DELETE /workingorders/{dealId}",
    # confirms
    "GET /confirms/{dealRef}",
    # watchlists
    "GET /watchlists",
    "POST /watchlists",
    "GET /watchlists/{id}",
    "PUT /watchlists/{id}",
    "DELETE /watchlists/{id}/{epic}",
    "DELETE /watchlists/{id}",
    # streaming (WebSocket)
    "WS marketData.subscribe",
    "WS OHLCMarketData.subscribe",
    "WS quotes (level cross)",
    "WS quotes (position epics)",
}


@dataclass
class Cells:
    """Test-node id covering each matrix cell, or None for untested/unsupported."""
    cli_pos: str | None = None
    cli_neg: str | None = None
    sdk_pos: str | None = None
    sdk_neg: str | None = None


# Coverage map: endpoint id -> Cells. Cells are populated by later tasks as tests
# land. SDK cells stay None for endpoints whose `sdk` is None (rendered as N/A).
# Node ids are "tests/<path>::<func>" (parametrized funcs use the base func name).
COVERAGE: dict[str, Cells] = {e.id: Cells() for e in ENDPOINTS}


def sdk_supported(endpoint_id: str) -> bool:
    """True if the SDK exposes this endpoint (so SDK cells are applicable)."""
    match = next((e for e in ENDPOINTS if e.id == endpoint_id), None)
    if match is None:
        raise KeyError(f"unknown endpoint id: {endpoint_id!r}")
    return match.sdk is not None
