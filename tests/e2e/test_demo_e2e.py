"""End-to-end tests against the real Capital.com DEMO API.

Opt-in only:

    CAPCTL_E2E=1 .venv/bin/pytest tests/e2e -m e2e -v

Requirements:
- a valid .env in the repo root (demo credentials)
- CAP_ALLOW_TRADING=true with BTCUSD allowed (or ALL)
- CAP_WS_ENABLED=true for the streaming test

Side effects on the DEMO account: creates and deletes one watchlist, and
opens, amends, and closes one minimum-size BTCUSD position. Tests are
order-dependent (numbered) and share state via the module-level _ctx dict.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

if not os.environ.get("CAPCTL_E2E"):
    pytest.skip("set CAPCTL_E2E=1 to run e2e tests", allow_module_level=True)

REPO = Path(__file__).resolve().parents[2]
ENV_FILE = REPO / ".env"
STATE_FILE = REPO / ".pytest_cache" / "e2e_state.json"
EPIC = "BTCUSD"  # trades 24/7, so the suite is not market-hours dependent

_ctx: dict = {}  # shared across the ordered tests in this module


def capctl(*args: str, expect_code: int = 0) -> dict:
    """Run `capctl --json <args>` as a real subprocess and parse stdout."""
    env = dict(
        os.environ,
        CAP_ENV_FILE=str(ENV_FILE),
        CAPCTL_STATE_FILE=str(STATE_FILE),
    )
    proc = subprocess.run(
        [sys.executable, "-m", "capital_cli", "--json", *args],
        capture_output=True,
        text=True,
        timeout=180,
        env=env,
        cwd=REPO,
    )
    assert proc.returncode == expect_code, (
        f"capctl {' '.join(args)} -> exit {proc.returncode}\n"
        f"stderr: {proc.stderr}\nstdout: {proc.stdout}"
    )
    # Each invocation is a fresh process that re-logins (POST /session is
    # limited to 1 req/s server-side); pace invocations to stay under it.
    time.sleep(1.2)
    return json.loads(proc.stdout) if proc.stdout.strip() else {}


def test_00_preconditions():
    assert ENV_FILE.is_file(), "copy demo credentials to .env first (Task 1)"
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.unlink(missing_ok=True)


def test_01_session_login():
    status = capctl("session", "status")
    assert status.get("env") == "demo", (
        "SAFETY: e2e suite must run against the demo environment, got: " + str(status)
    )
    data = capctl("session", "login")
    assert data.get("active_account_id"), data


def test_02_account_list():
    data = capctl("account", "list")
    accounts = data.get("accounts", [])
    assert accounts, data
    assert data.get("active_account_id")


def test_03_market_search():
    data = capctl("market", "search", "bitcoin", "--limit", "5")
    assert data.get("markets"), data
    assert len(data["markets"]) <= 5


def test_04_market_get():
    data = capctl("market", "get", EPIC)
    assert data.get("instrument", {}).get("epic") == EPIC, data
    assert "dealingRules" in data
    assert "snapshot" in data


def test_05_market_prices():
    data = capctl("market", "prices", EPIC, "--resolution", "HOUR", "--max", "10")
    assert data.get("prices"), data
    assert len(data["prices"]) <= 10


def test_06_market_sentiment():
    data = capctl("market", "sentiment", EPIC)
    assert "longPositionPercentage" in data, data


def test_07_positions_list():
    data = capctl("trade", "positions")
    assert "positions" in data, data


def test_08_orders_list():
    data = capctl("trade", "orders")
    assert "workingOrders" in data, data


def test_09_watchlist_lifecycle():
    created = capctl("watchlist", "create", "capctl-e2e", "--yes")
    wl_id = created.get("watchlistId") or created.get("id")
    assert wl_id, created
    wl_id = str(wl_id)
    try:
        capctl("watchlist", "add", wl_id, EPIC, "--yes")
        got = capctl("watchlist", "get", wl_id)
        epics = [m.get("epic") for m in got.get("markets", [])]
        assert EPIC in epics, got
        capctl("watchlist", "remove", wl_id, EPIC, "--yes")
    finally:
        capctl("watchlist", "delete", wl_id, "--yes")


def test_10_preview_position():
    data = capctl("trade", "preview-position", EPIC, "BUY", "0.001")
    assert data.get("all_checks_passed") is True, data.get("checks")
    assert data.get("preview_id")
    _ctx["preview_id"] = data["preview_id"]


def test_11_execute_position():
    """Opens a real (minimum-size) BTCUSD position on the DEMO account."""
    data = capctl("trade", "execute-position", _ctx["preview_id"], "--yes", "--timeout", "30")
    assert data.get("dealReference"), data
    conf = data.get("confirmation") or {}
    assert conf.get("status") == "ACCEPTED", conf

    # For an OPEN, the top-level "dealId" is an internal order reference that
    # does NOT match the resulting position's dealId in /positions; the
    # correct dealId is in affectedDeals[0] (status "OPENED"). Prefer
    # affectedDeals first; fall back to the top-level dealId, then to a
    # deal-reference lookup against /positions as a last resort.
    affected = conf.get("affectedDeals") or []
    deal_id = affected[0].get("dealId") if affected else None
    if not deal_id:
        deal_id = conf.get("dealId")
    if not deal_id:
        # Last resort: find the position by deal reference.
        positions = capctl("trade", "positions")
        for p in positions.get("positions", []):
            if p.get("position", {}).get("dealReference") == data["dealReference"]:
                deal_id = p["position"]["dealId"]
    assert deal_id, f"could not determine dealId from {conf}"
    _ctx["deal_id"] = deal_id


def test_12_position_visible():
    data = capctl("trade", "positions")
    ids = [p.get("position", {}).get("dealId") for p in data.get("positions", [])]
    assert _ctx["deal_id"] in ids, ids


def test_13_amend_position():
    """Amend the open position's stop/limit to safe far-from-market levels."""
    pos = capctl("trade", "position", _ctx["deal_id"])
    level = float(pos["position"]["level"])  # current/open price
    stop = round(level * 0.5, 1)             # far below — won't trigger
    profit = round(level * 1.5, 1)           # far above — won't trigger
    data = capctl(
        "trade", "amend-position", _ctx["deal_id"],
        "--stop-level", str(stop),
        "--profit-level", str(profit),
        "--yes", "--timeout", "30",
    )
    conf = data.get("confirmation") or {}
    assert conf.get("status") == "ACCEPTED", conf


def test_14_close_position():
    data = capctl("trade", "close", _ctx["deal_id"], "--yes", "--timeout", "30")
    conf = data.get("confirmation") or {}
    assert conf.get("status") == "ACCEPTED", conf


def test_15_position_gone():
    data = capctl("trade", "positions")
    ids = [p.get("position", {}).get("dealId") for p in data.get("positions", [])]
    assert _ctx["deal_id"] not in ids, ids


def test_16_stream_prices():
    """15-second live stream; BTCUSD ticks frequently enough to collect >=1."""
    data = capctl("stream", "prices", EPIC, "--duration", "15", "--interval", "1")
    assert data.get("ticks_received", 0) >= 1, data
    assert data.get("ticks"), data


def test_17_history_activity():
    data = capctl("account", "history-activity", "--last", "3600")
    assert "activities" in data, data


def test_18_history_activity_detailed():
    data = capctl("account", "history-activity", "--last", "3600", "--detailed")
    assert "activities" in data, data


def test_19_session_details():
    data = capctl("session", "details")
    assert data.get("clientId") or data.get("accountId"), data


def test_20_session_time():
    data = capctl("session", "time")
    assert data, data  # non-empty dict (serverTime or wrapped value)


def test_21_session_encryption_key():
    data = capctl("session", "encryption-key")
    assert data.get("encryptionKey"), data


def test_22_sentiment_batch():
    data = capctl("market", "sentiment", "BTCUSD,ETHUSD")
    sents = data.get("clientSentiments")
    assert sents, data
    assert len(sents) >= 1


def test_23_logout():
    capctl("session", "logout")
