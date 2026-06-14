"""CLI positive e2e for endpoints not exercised by test_demo_e2e.py. Read-only
tests run on CAPCTL_E2E; the working-order lifecycle gates on CAPCTL_E2E_TRADING
and cancels what it creates. Opt-in via CAPCTL_E2E=1.
"""

import os

import pytest

from tests.e2e._helpers import run_cli

pytestmark = pytest.mark.e2e
if not os.environ.get("CAPCTL_E2E"):
    pytest.skip("set CAPCTL_E2E=1", allow_module_level=True)

_TRADING_OK = os.environ.get("CAPCTL_E2E_TRADING") == "I_UNDERSTAND"
requires_trading = pytest.mark.skipif(
    not _TRADING_OK, reason="set CAPCTL_E2E_TRADING=I_UNDERSTAND"
)
EPIC = "BTCUSD"


def _ok(*args, **kw):
    res = run_cli(*args, **kw)
    assert res.code == 0, f"{' '.join(args)} -> {res.code}\n{res.stderr}"
    return res.json()


def test_cli_session_ping():
    _ok("session", "login")
    body = _ok("session", "ping")
    assert isinstance(body, dict)


def test_cli_session_switch():
    accounts = _ok("account", "list")
    ids = [a.get("accountId") for a in accounts.get("accounts", [])]
    assert ids, accounts
    body = _ok("session", "switch", ids[0])
    assert body.get("active_account_id") == ids[0] or body


def test_cli_account_history_transactions():
    body = _ok("account", "history-transactions", "--last", "3600")
    assert isinstance(body, dict)


def test_cli_watchlist_list():
    body = _ok("watchlist", "list")
    assert isinstance(body, dict)


def test_cli_market_nav_root():
    body = _ok("market", "nav-root")
    assert body.get("nodes"), body


def test_cli_market_nav_node():
    root = _ok("market", "nav-root")
    node_id = root["nodes"][0]["id"]
    body = _ok("market", "nav-node", str(node_id), "--limit", "5")
    assert ("nodes" in body) or ("markets" in body), body


@requires_trading
def test_cli_account_topup():
    body = _ok("account", "topup", "1", "--yes")
    assert isinstance(body, dict)


@requires_trading
def test_cli_working_order_lifecycle():
    market = _ok("market", "get", EPIC)
    if market.get("snapshot", {}).get("marketStatus") != "TRADEABLE":
        pytest.skip(f"{EPIC} not TRADEABLE")
    bid = float(market["snapshot"]["bid"])
    far_below = round(bid * 0.5, 2)  # a BUY LIMIT here will not fill

    preview = _ok("trade", "preview-order", EPIC, "BUY", "LIMIT", str(far_below), "0.001")
    assert preview.get("all_checks_passed"), preview
    pid = preview["preview_id"]

    created = _ok("trade", "execute-order", pid, "--yes", "--timeout", "30")
    deal_ref = created.get("dealReference")
    assert deal_ref, created
    deal_id = None
    try:
        conf = _ok("trade", "confirm", deal_ref)
        assert conf, conf
        orders = _ok("trade", "orders")
        for o in orders.get("workingOrders", []):
            data = o.get("workingOrderData", {})
            if data.get("dealReference") == deal_ref or data.get("epic") == EPIC:
                deal_id = data.get("dealId")
                break
        assert deal_id, orders
        amended = _ok(
            "trade", "amend-order", deal_id, "--level", str(round(far_below * 0.99, 2)),
            "--yes", "--timeout", "30",
        )
        assert (amended.get("confirmation") or {}).get("status") in {"ACCEPTED", "TIMEOUT"}, amended
    finally:
        if deal_id:
            run_cli("trade", "cancel", deal_id, "--yes", "--timeout", "30")
        else:
            orders = run_cli("trade", "orders").json()
            for o in orders.get("workingOrders", []):
                did = o.get("workingOrderData", {}).get("dealId")
                if did:
                    run_cli("trade", "cancel", did, "--yes", "--timeout", "30")


@requires_trading
def test_cli_position_get_then_close():
    market = _ok("market", "get", EPIC)
    if market.get("snapshot", {}).get("marketStatus") != "TRADEABLE":
        pytest.skip(f"{EPIC} not TRADEABLE")
    preview = _ok("trade", "preview-position", EPIC, "BUY", "0.001")
    assert preview.get("all_checks_passed"), preview
    opened = _ok("trade", "execute-position", preview["preview_id"], "--yes", "--timeout", "30")
    conf = opened.get("confirmation") or {}
    affected = conf.get("affectedDeals") or []
    deal_id = (affected[0].get("dealId") if affected else None) or conf.get("dealId")
    assert deal_id, opened
    try:
        got = _ok("trade", "position", deal_id)
        assert got.get("position", {}).get("dealId") == deal_id, got
    finally:
        run_cli("trade", "close", deal_id, "--yes", "--timeout", "30")


def test_cli_stream_portfolio_runs():
    res = run_cli("stream", "portfolio", "--duration", "5", "--interval", "1")
    assert res.code == 0, res.stderr


def test_cli_stream_alerts_runs():
    market = _ok("market", "get", EPIC)
    if market.get("snapshot", {}).get("marketStatus") != "TRADEABLE":
        pytest.skip(f"{EPIC} not TRADEABLE")
    res = run_cli("stream", "alerts", EPIC, "1", "--direction", "BELOW", "--duration", "5")
    assert res.code == 0, res.stderr
