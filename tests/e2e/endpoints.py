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


# --- cli_neg wiring (Task 3): one canonical negative test per endpoint --------
_N = "tests/e2e/test_cli_negative_e2e.py"
COVERAGE["session.time"].cli_neg = f"{_N}::test_cli_usage_error[session.time]"
COVERAGE["session.ping"].cli_neg = f"{_N}::test_cli_missing_config[session.ping]"
COVERAGE["session.details"].cli_neg = f"{_N}::test_cli_missing_config[session.details]"
COVERAGE["session.encryption_key"].cli_neg = f"{_N}::test_cli_usage_error[session.encryption_key]"
COVERAGE["session.login"].cli_neg = f"{_N}::test_cli_missing_config[session.login]"
COVERAGE["session.switch"].cli_neg = f"{_N}::test_cli_bad_identifier_is_rejected[session.switch]"
COVERAGE["session.logout"].cli_neg = f"{_N}::test_cli_usage_error[session.logout]"
COVERAGE["account.list"].cli_neg = f"{_N}::test_cli_missing_config[account.list]"
COVERAGE["account.prefs_get"].cli_neg = f"{_N}::test_cli_missing_config[account.prefs_get]"
COVERAGE["account.prefs_set"].cli_neg = f"{_N}::test_cli_guard_blocks_mutation[account.prefs_set]"
COVERAGE["account.history_activity"].cli_neg = f"{_N}::test_cli_usage_error[account.history_activity]"
COVERAGE["account.history_transactions"].cli_neg = f"{_N}::test_cli_missing_config[account.history_transactions]"
COVERAGE["account.topup"].cli_neg = f"{_N}::test_cli_guard_blocks_mutation[account.topup]"
COVERAGE["market.search"].cli_neg = f"{_N}::test_cli_invalid_arguments_rejected[market.search]"
COVERAGE["market.get"].cli_neg = f"{_N}::test_cli_bad_identifier_is_rejected[market.get]"
COVERAGE["market.nav_root"].cli_neg = f"{_N}::test_cli_missing_config[market.nav_root]"
COVERAGE["market.nav_node"].cli_neg = f"{_N}::test_cli_bad_identifier_is_rejected[market.nav_node]"
COVERAGE["market.prices"].cli_neg = f"{_N}::test_cli_bad_identifier_is_rejected[market.prices]"
COVERAGE["market.sentiment"].cli_neg = f"{_N}::test_cli_bad_identifier_is_rejected[market.sentiment]"
COVERAGE["position.list"].cli_neg = f"{_N}::test_cli_invalid_arguments_rejected[position.list]"
COVERAGE["position.get"].cli_neg = f"{_N}::test_cli_bad_identifier_is_rejected[position.get]"
COVERAGE["position.preview"].cli_neg = f"{_N}::test_cli_invalid_arguments_rejected[position.preview]"
COVERAGE["position.execute"].cli_neg = f"{_N}::test_cli_guard_blocks_mutation[position.execute]"
COVERAGE["position.amend"].cli_neg = f"{_N}::test_cli_guard_blocks_mutation[position.amend]"
COVERAGE["position.close"].cli_neg = f"{_N}::test_cli_guard_blocks_mutation[position.close]"
COVERAGE["order.list"].cli_neg = f"{_N}::test_cli_invalid_arguments_rejected[order.list]"
COVERAGE["order.preview"].cli_neg = f"{_N}::test_cli_invalid_arguments_rejected[order.preview]"
COVERAGE["order.execute"].cli_neg = f"{_N}::test_cli_guard_blocks_mutation[order.execute]"
COVERAGE["order.amend"].cli_neg = f"{_N}::test_cli_guard_blocks_mutation[order.amend]"
COVERAGE["order.cancel"].cli_neg = f"{_N}::test_cli_guard_blocks_mutation[order.cancel]"
COVERAGE["trade.confirm"].cli_neg = f"{_N}::test_cli_bad_identifier_is_rejected[trade.confirm]"
COVERAGE["watchlist.list"].cli_neg = f"{_N}::test_cli_missing_config[watchlist.list]"
COVERAGE["watchlist.create"].cli_neg = f"{_N}::test_cli_guard_blocks_mutation[watchlist.create]"
COVERAGE["watchlist.get"].cli_neg = f"{_N}::test_cli_bad_identifier_is_rejected[watchlist.get]"
COVERAGE["watchlist.add"].cli_neg = f"{_N}::test_cli_guard_blocks_mutation[watchlist.add]"
COVERAGE["watchlist.remove"].cli_neg = f"{_N}::test_cli_guard_blocks_mutation[watchlist.remove]"
COVERAGE["watchlist.delete"].cli_neg = f"{_N}::test_cli_guard_blocks_mutation[watchlist.delete]"
COVERAGE["stream.prices"].cli_neg = f"{_N}::test_cli_usage_error[stream.prices]"
COVERAGE["stream.candles"].cli_neg = f"{_N}::test_cli_invalid_arguments_rejected[stream.candles]"
COVERAGE["stream.alerts"].cli_neg = f"{_N}::test_cli_invalid_arguments_rejected[stream.alerts]"
COVERAGE["stream.portfolio"].cli_neg = f"{_N}::test_cli_usage_error[stream.portfolio]"


# --- cli_pos wiring (Task 4): existing demo-e2e + new gap tests ---------------
_D = "tests/e2e/test_demo_e2e.py"
_G = "tests/e2e/test_cli_positive_gaps_e2e.py"
COVERAGE["session.time"].cli_pos = f"{_D}::test_20_session_time"
COVERAGE["session.ping"].cli_pos = f"{_G}::test_cli_session_ping"
COVERAGE["session.details"].cli_pos = f"{_D}::test_19_session_details"
COVERAGE["session.encryption_key"].cli_pos = f"{_D}::test_21_session_encryption_key"
COVERAGE["session.login"].cli_pos = f"{_D}::test_01_session_login"
COVERAGE["session.switch"].cli_pos = f"{_G}::test_cli_session_switch"
COVERAGE["session.logout"].cli_pos = f"{_D}::test_27_logout"
COVERAGE["account.list"].cli_pos = f"{_D}::test_02_account_list"
COVERAGE["account.prefs_get"].cli_pos = f"{_D}::test_24_leverage_roundtrip"
COVERAGE["account.prefs_set"].cli_pos = f"{_D}::test_24_leverage_roundtrip"
COVERAGE["account.history_activity"].cli_pos = f"{_D}::test_17_history_activity"
COVERAGE["account.history_transactions"].cli_pos = f"{_G}::test_cli_account_history_transactions"
COVERAGE["account.topup"].cli_pos = f"{_G}::test_cli_account_topup"
COVERAGE["market.search"].cli_pos = f"{_D}::test_03_market_search"
COVERAGE["market.get"].cli_pos = f"{_D}::test_04_market_get"
COVERAGE["market.nav_root"].cli_pos = f"{_G}::test_cli_market_nav_root"
COVERAGE["market.nav_node"].cli_pos = f"{_G}::test_cli_market_nav_node"
COVERAGE["market.prices"].cli_pos = f"{_D}::test_05_market_prices"
COVERAGE["market.sentiment"].cli_pos = f"{_D}::test_06_market_sentiment"
COVERAGE["position.list"].cli_pos = f"{_D}::test_07_positions_list"
COVERAGE["position.get"].cli_pos = f"{_G}::test_cli_position_get_then_close"
COVERAGE["position.preview"].cli_pos = f"{_D}::test_10_preview_position"
COVERAGE["position.execute"].cli_pos = f"{_D}::test_11_execute_position"
COVERAGE["position.amend"].cli_pos = f"{_D}::test_13_amend_position"
COVERAGE["position.close"].cli_pos = f"{_D}::test_14_close_position"
COVERAGE["order.list"].cli_pos = f"{_D}::test_08_orders_list"
COVERAGE["order.preview"].cli_pos = f"{_G}::test_cli_working_order_lifecycle"
COVERAGE["order.execute"].cli_pos = f"{_G}::test_cli_working_order_lifecycle"
COVERAGE["order.amend"].cli_pos = f"{_G}::test_cli_working_order_lifecycle"
COVERAGE["order.cancel"].cli_pos = f"{_G}::test_cli_working_order_lifecycle"
COVERAGE["trade.confirm"].cli_pos = f"{_G}::test_cli_working_order_lifecycle"
COVERAGE["watchlist.list"].cli_pos = f"{_G}::test_cli_watchlist_list"
COVERAGE["watchlist.create"].cli_pos = f"{_D}::test_09_watchlist_lifecycle"
COVERAGE["watchlist.get"].cli_pos = f"{_D}::test_09_watchlist_lifecycle"
COVERAGE["watchlist.add"].cli_pos = f"{_D}::test_09_watchlist_lifecycle"
COVERAGE["watchlist.remove"].cli_pos = f"{_D}::test_09_watchlist_lifecycle"
COVERAGE["watchlist.delete"].cli_pos = f"{_D}::test_09_watchlist_lifecycle"
COVERAGE["stream.prices"].cli_pos = f"{_D}::test_16_stream_prices"
COVERAGE["stream.candles"].cli_pos = f"{_D}::test_23_stream_candles"
COVERAGE["stream.alerts"].cli_pos = f"{_G}::test_cli_stream_alerts_runs"
COVERAGE["stream.portfolio"].cli_pos = f"{_G}::test_cli_stream_portfolio_runs"


# --- sdk_pos wiring (Task 5): existing sdk-e2e + new gap tests -----------------
_S = "tests/e2e/test_sdk_e2e.py"
_P = "tests/e2e/test_sdk_positive_gaps_e2e.py"
COVERAGE["session.ping"].sdk_pos = f"{_P}::test_sdk_session_ping_switch_logout"
COVERAGE["session.login"].sdk_pos = f"{_S}::test_sdk_read_only_flow"
COVERAGE["session.switch"].sdk_pos = f"{_P}::test_sdk_session_ping_switch_logout"
COVERAGE["session.logout"].sdk_pos = f"{_P}::test_sdk_session_ping_switch_logout"
COVERAGE["account.list"].sdk_pos = f"{_S}::test_sdk_read_only_flow"
COVERAGE["account.prefs_get"].sdk_pos = f"{_P}::test_sdk_account_prefs_and_history"
COVERAGE["account.prefs_set"].sdk_pos = f"{_P}::test_sdk_prefs_roundtrip_and_topup"
COVERAGE["account.history_activity"].sdk_pos = f"{_P}::test_sdk_account_prefs_and_history"
COVERAGE["account.history_transactions"].sdk_pos = f"{_P}::test_sdk_account_prefs_and_history"
COVERAGE["account.topup"].sdk_pos = f"{_P}::test_sdk_prefs_roundtrip_and_topup"
COVERAGE["market.search"].sdk_pos = f"{_S}::test_sdk_markets_and_prices"
COVERAGE["market.get"].sdk_pos = f"{_S}::test_sdk_read_only_flow"
COVERAGE["market.nav_root"].sdk_pos = f"{_P}::test_sdk_market_sentiment_and_navigation"
COVERAGE["market.nav_node"].sdk_pos = f"{_P}::test_sdk_market_sentiment_and_navigation"
COVERAGE["market.prices"].sdk_pos = f"{_S}::test_sdk_markets_and_prices"
COVERAGE["market.sentiment"].sdk_pos = f"{_P}::test_sdk_market_sentiment_and_navigation"
COVERAGE["position.list"].sdk_pos = f"{_S}::test_sdk_read_only_flow"
COVERAGE["position.get"].sdk_pos = f"{_P}::test_sdk_position_get_amend_close"
COVERAGE["position.preview"].sdk_pos = f"{_S}::test_sdk_trading_preview_only"
COVERAGE["position.execute"].sdk_pos = f"{_S}::test_sdk_trade_lifecycle_leaves_account_flat"
COVERAGE["position.amend"].sdk_pos = f"{_P}::test_sdk_position_get_amend_close"
COVERAGE["position.close"].sdk_pos = f"{_S}::test_sdk_trade_lifecycle_leaves_account_flat"
COVERAGE["order.list"].sdk_pos = f"{_P}::test_sdk_orders_list"
COVERAGE["order.preview"].sdk_pos = f"{_P}::test_sdk_working_order_lifecycle_and_confirm"
COVERAGE["order.execute"].sdk_pos = f"{_P}::test_sdk_working_order_lifecycle_and_confirm"
COVERAGE["order.amend"].sdk_pos = f"{_P}::test_sdk_working_order_lifecycle_and_confirm"
COVERAGE["order.cancel"].sdk_pos = f"{_P}::test_sdk_working_order_lifecycle_and_confirm"
COVERAGE["trade.confirm"].sdk_pos = f"{_P}::test_sdk_working_order_lifecycle_and_confirm"
COVERAGE["watchlist.list"].sdk_pos = f"{_P}::test_sdk_watchlist_list"
COVERAGE["watchlist.create"].sdk_pos = f"{_S}::test_sdk_watchlist_lifecycle"
COVERAGE["watchlist.get"].sdk_pos = f"{_S}::test_sdk_watchlist_lifecycle"
COVERAGE["watchlist.add"].sdk_pos = f"{_S}::test_sdk_watchlist_lifecycle"
COVERAGE["watchlist.remove"].sdk_pos = f"{_S}::test_sdk_watchlist_lifecycle"
COVERAGE["watchlist.delete"].sdk_pos = f"{_S}::test_sdk_watchlist_lifecycle"
COVERAGE["stream.prices"].sdk_pos = f"{_S}::test_sdk_stream_prices_short"
COVERAGE["stream.candles"].sdk_pos = f"{_P}::test_sdk_stream_candles_short"
COVERAGE["stream.alerts"].sdk_pos = f"{_P}::test_sdk_stream_alerts_short"
COVERAGE["stream.portfolio"].sdk_pos = f"{_P}::test_sdk_stream_portfolio_short"


# --- sdk_neg wiring (Task 6): bad-id / validation / guard / auth / stream ------
_SN = "tests/e2e/test_sdk_negative_e2e.py"
COVERAGE["market.get"].sdk_neg = f"{_SN}::test_sdk_bad_identifier_raises[market.get]"
COVERAGE["market.prices"].sdk_neg = f"{_SN}::test_sdk_bad_identifier_raises[market.prices]"
COVERAGE["market.nav_node"].sdk_neg = f"{_SN}::test_sdk_missing_config_raises[market.nav_node]"
COVERAGE["position.get"].sdk_neg = f"{_SN}::test_sdk_bad_identifier_raises[position.get]"
COVERAGE["watchlist.get"].sdk_neg = f"{_SN}::test_sdk_bad_identifier_raises[watchlist.get]"
COVERAGE["trade.confirm"].sdk_neg = f"{_SN}::test_sdk_bad_identifier_raises[trade.confirm]"
COVERAGE["position.preview"].sdk_neg = f"{_SN}::test_sdk_preview_position_invalid_size"
COVERAGE["order.preview"].sdk_neg = f"{_SN}::test_sdk_preview_order_invalid"
COVERAGE["position.execute"].sdk_neg = f"{_SN}::test_sdk_execute_position_trading_disabled"
COVERAGE["order.execute"].sdk_neg = f"{_SN}::test_sdk_execute_order_trading_disabled"
COVERAGE["position.close"].sdk_neg = f"{_SN}::test_sdk_close_trading_disabled"
COVERAGE["order.cancel"].sdk_neg = f"{_SN}::test_sdk_trade_mutations_trading_disabled[order.cancel]"
COVERAGE["position.amend"].sdk_neg = f"{_SN}::test_sdk_trade_mutations_trading_disabled[position.amend]"
COVERAGE["order.amend"].sdk_neg = f"{_SN}::test_sdk_trade_mutations_trading_disabled[order.amend]"
COVERAGE["watchlist.create"].sdk_neg = f"{_SN}::test_sdk_nontrade_mutations_require_confirm[watchlist.create]"
COVERAGE["watchlist.add"].sdk_neg = f"{_SN}::test_sdk_nontrade_mutations_require_confirm[watchlist.add]"
COVERAGE["watchlist.remove"].sdk_neg = f"{_SN}::test_sdk_nontrade_mutations_require_confirm[watchlist.remove]"
COVERAGE["watchlist.delete"].sdk_neg = f"{_SN}::test_sdk_nontrade_mutations_require_confirm[watchlist.delete]"
COVERAGE["account.prefs_set"].sdk_neg = f"{_SN}::test_sdk_nontrade_mutations_require_confirm[account.prefs_set]"
COVERAGE["account.topup"].sdk_neg = f"{_SN}::test_sdk_nontrade_mutations_require_confirm[account.topup]"
COVERAGE["session.ping"].sdk_neg = f"{_SN}::test_sdk_missing_config_raises[session.ping]"
COVERAGE["session.switch"].sdk_neg = f"{_SN}::test_sdk_missing_config_raises[session.switch]"
COVERAGE["session.logout"].sdk_neg = f"{_SN}::test_sdk_missing_config_raises[session.logout]"
COVERAGE["session.login"].sdk_neg = f"{_SN}::test_sdk_missing_config_raises[session.login]"
COVERAGE["account.list"].sdk_neg = f"{_SN}::test_sdk_missing_config_raises[account.list]"
COVERAGE["account.prefs_get"].sdk_neg = f"{_SN}::test_sdk_missing_config_raises[account.prefs_get]"
COVERAGE["account.history_activity"].sdk_neg = f"{_SN}::test_sdk_missing_config_raises[account.history_activity]"
COVERAGE["account.history_transactions"].sdk_neg = f"{_SN}::test_sdk_missing_config_raises[account.history_transactions]"
COVERAGE["market.search"].sdk_neg = f"{_SN}::test_sdk_missing_config_raises[market.search]"
COVERAGE["market.sentiment"].sdk_neg = f"{_SN}::test_sdk_missing_config_raises[market.sentiment]"
COVERAGE["market.nav_root"].sdk_neg = f"{_SN}::test_sdk_missing_config_raises[market.nav_root]"
COVERAGE["position.list"].sdk_neg = f"{_SN}::test_sdk_missing_config_raises[position.list]"
COVERAGE["order.list"].sdk_neg = f"{_SN}::test_sdk_missing_config_raises[order.list]"
COVERAGE["watchlist.list"].sdk_neg = f"{_SN}::test_sdk_missing_config_raises[watchlist.list]"
COVERAGE["stream.prices"].sdk_neg = f"{_SN}::test_sdk_missing_config_raises[stream.prices]"
COVERAGE["stream.candles"].sdk_neg = f"{_SN}::test_sdk_missing_config_raises[stream.candles]"
COVERAGE["stream.alerts"].sdk_neg = f"{_SN}::test_sdk_missing_config_raises[stream.alerts]"
COVERAGE["stream.portfolio"].sdk_neg = f"{_SN}::test_sdk_missing_config_raises[stream.portfolio]"


def sdk_supported(endpoint_id: str) -> bool:
    """True if the SDK exposes this endpoint (so SDK cells are applicable)."""
    match = next((e for e in ENDPOINTS if e.id == endpoint_id), None)
    if match is None:
        raise KeyError(f"unknown endpoint id: {endpoint_id!r}")
    return match.sdk is not None
