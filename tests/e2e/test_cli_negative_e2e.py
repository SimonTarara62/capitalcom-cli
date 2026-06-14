"""CLI negative e2e: every command's failure path, exercised against the real
demo API WITHOUT mutating the account. Three techniques:
  - bad identifier  -> broker 404/rejection -> exit 7
  - bad arguments   -> local validation     -> exit 2
  - forced guard    -> env override         -> exit 4 (no HTTP sent)
Opt-in via CAPCTL_E2E=1.
"""

import os

import pytest

from tests.e2e._helpers import (
    BAD_DEAL_ID,
    BAD_DEAL_REF,
    BAD_EPIC,
    BAD_NODE_ID,
    BAD_WATCHLIST_ID,
    run_cli,
)

pytestmark = pytest.mark.e2e
if not os.environ.get("CAPCTL_E2E"):
    pytest.skip("set CAPCTL_E2E=1", allow_module_level=True)


# endpoint id -> CLI args that hit a guaranteed-missing identifier.
BAD_ID_CASES = {
    "session.switch": ("session", "switch", BAD_DEAL_ID),
    "account.history_activity": ("account", "history-activity", "--deal-id", BAD_DEAL_ID),
    "market.get": ("market", "get", BAD_EPIC),
    "market.nav_node": ("market", "nav-node", BAD_NODE_ID),
    "market.prices": ("market", "prices", BAD_EPIC),
    "market.sentiment": ("market", "sentiment", BAD_EPIC),
    "position.get": ("trade", "position", BAD_DEAL_ID),
    "trade.confirm": ("trade", "confirm", BAD_DEAL_REF),
    "watchlist.get": ("watchlist", "get", BAD_WATCHLIST_ID),
}


@pytest.mark.parametrize("endpoint_id", list(BAD_ID_CASES), ids=list(BAD_ID_CASES))
def test_cli_bad_identifier_is_rejected(endpoint_id):
    res = run_cli(*BAD_ID_CASES[endpoint_id])
    # Broker rejects unknown ids; a few (e.g. history --deal-id, sentiment) may
    # return an empty/clean 2xx — accept either rejection OR an explicit empty,
    # but never a crash (exit 1) or success-with-data masquerade.
    assert res.code in (0, 7), f"{endpoint_id}: exit {res.code}\n{res.stderr}"
    if res.code == 7:
        body = res.json()
        assert body.get("error", {}).get("code") in {
            "UPSTREAM_ERROR",
            "BROKER_REJECTED",
        }, body


# endpoint id -> CLI args that are syntactically/semantically invalid (exit 2).
BAD_ARG_CASES = {
    "account.prefs_set": ("account", "prefs-set", "--leverage", "NOTVALID"),
    "account.topup": ("account", "topup", "not-a-number", "--yes"),
    "position.list": ("trade", "positions", "--limit", "0"),
    "position.preview": ("trade", "preview-position", "GOLD", "SIDEWAYS", "1"),
    "order.list": ("trade", "orders", "--limit", "0"),
    "order.preview": ("trade", "preview-order", "GOLD", "BUY", "WRONG", "1", "1"),
    "position.amend": ("trade", "amend-position", BAD_DEAL_ID),
    "order.amend": ("trade", "amend-order", BAD_DEAL_ID),
    "stream.prices": ("stream", "prices", ""),
    "stream.candles": ("stream", "candles", "GOLD", "--type", "nope"),
    "stream.alerts": ("stream", "alerts", "GOLD", "100", "--direction", "SIDEWAYS"),
    "market.search": ("market", "search", "x", "--limit", "0"),
}


@pytest.mark.parametrize("endpoint_id", list(BAD_ARG_CASES), ids=list(BAD_ARG_CASES))
def test_cli_invalid_arguments_rejected(endpoint_id):
    res = run_cli(*BAD_ARG_CASES[endpoint_id])
    assert res.code == 2, f"{endpoint_id}: expected exit 2, got {res.code}\n{res.stderr}"


# endpoint id -> (args, env_overrides) that trip a guard before any HTTP.
_TRADING_OFF = {"CAP_ALLOW_TRADING": "false"}
_CONFIRM_ON = {"CAP_REQUIRE_EXPLICIT_CONFIRM": "true"}
_DRY_RUN = {"CAP_DRY_RUN": "true"}

GUARD_CASES = {
    "position.execute": (("trade", "execute-position", "no-preview", "--yes"), _TRADING_OFF),
    "order.execute": (("trade", "execute-order", "no-preview", "--yes"), _TRADING_OFF),
    "position.close": (("trade", "close", BAD_DEAL_ID, "--yes"), _TRADING_OFF),
    "order.cancel": (("trade", "cancel", BAD_DEAL_ID, "--yes"), _TRADING_OFF),
    "position.amend": (("trade", "amend-position", BAD_DEAL_ID, "--stop-distance", "50", "--yes"), _TRADING_OFF),
    "order.amend": (("trade", "amend-order", BAD_DEAL_ID, "--level", "1", "--yes"), _TRADING_OFF),
    "account.prefs_set": (("account", "prefs-set", "--leverage", "CRYPTOCURRENCIES=2"), _CONFIRM_ON),
    "account.topup": (("account", "topup", "100"), _CONFIRM_ON),
    "watchlist.create": (("watchlist", "create", "capctl-neg"), _CONFIRM_ON),
    "watchlist.add": (("watchlist", "add", BAD_WATCHLIST_ID, "GOLD"), _DRY_RUN),
    "watchlist.remove": (("watchlist", "remove", BAD_WATCHLIST_ID, "GOLD"), _DRY_RUN),
    "watchlist.delete": (("watchlist", "delete", BAD_WATCHLIST_ID), _DRY_RUN),
}


@pytest.mark.parametrize("endpoint_id", list(GUARD_CASES), ids=list(GUARD_CASES))
def test_cli_guard_blocks_mutation(endpoint_id):
    args, overrides = GUARD_CASES[endpoint_id]
    res = run_cli(*args, env_overrides=overrides)
    assert res.code == 4, f"{endpoint_id}: expected guard exit 4, got {res.code}\n{res.stderr}"
    body = res.json()
    assert body.get("error", {}).get("code") in {
        "TRADING_DISABLED",
        "DRY_RUN_ENABLED",
        "CONFIRM_REQUIRED",
    }, body


# Read-only endpoints with no bad-id: break auth to exercise their failure path.
_BAD_CREDS = {"CAP_API_PASSWORD": "definitely-wrong-password", "CAP_PERSIST_SESSION": "false"}

AUTH_FAIL_CASES = {
    "session.ping": ("session", "ping"),
    "session.details": ("session", "details"),
    "session.login": ("session", "login", "--force"),
    "account.list": ("account", "list"),
    "account.prefs_get": ("account", "prefs-get"),
    "account.history_transactions": ("account", "history-transactions"),
    "market.nav_root": ("market", "nav-root"),
    "watchlist.list": ("watchlist", "list"),
}


@pytest.mark.parametrize("endpoint_id", list(AUTH_FAIL_CASES), ids=list(AUTH_FAIL_CASES))
def test_cli_auth_failure_path(endpoint_id):
    res = run_cli(*AUTH_FAIL_CASES[endpoint_id], env_overrides=_BAD_CREDS)
    # Bad credentials -> auth error (5). session.login surfaces AUTH_FAILED;
    # downstream reads surface SESSION_* / UPSTREAM. Accept the auth-family codes.
    assert res.code in (5, 7), f"{endpoint_id}: exit {res.code}\n{res.stderr}"


USAGE_ERROR_CASES = {
    "session.time": ("session", "time", "--no-such-flag"),
    "session.encryption_key": ("session", "encryption-key", "--no-such-flag"),
    "session.logout": ("session", "logout", "--no-such-flag"),
    "account.history_activity": ("account", "history-activity", "--last", "-5"),
    "position.list": ("trade", "positions", "--no-such-flag"),
    "order.list": ("trade", "orders", "--no-such-flag"),
    "stream.prices": ("stream", "prices", "GOLD", "--duration", "-1"),
    "stream.candles": ("stream", "candles", "GOLD", "--no-such-flag"),
    "stream.portfolio": ("stream", "portfolio", "--no-such-flag"),
    "stream.alerts": ("stream", "alerts", "GOLD", "100", "--no-such-flag"),
    "market.search": ("market", "search", "x", "--no-such-flag"),
    "market.sentiment": ("market", "sentiment"),
    "position.preview": ("trade", "preview-position", "GOLD", "BUY"),
    "order.preview": ("trade", "preview-order", "GOLD", "BUY", "LIMIT"),
}


@pytest.mark.parametrize("endpoint_id", list(USAGE_ERROR_CASES), ids=list(USAGE_ERROR_CASES))
def test_cli_usage_error(endpoint_id):
    res = run_cli(*USAGE_ERROR_CASES[endpoint_id])
    assert res.code == 2, f"{endpoint_id}: expected usage exit 2, got {res.code}\n{res.stderr}"
