"""Opt-in: drive the demo API through the SDK facade (no CLI subprocess).

    CAPCTL_E2E=1 .venv/bin/pytest tests/e2e/test_sdk_e2e.py -m e2e -v

This is the exact in-process path an MCP server uses: it imports
``capital_cli.sdk`` and calls the services directly, rather than subprocessing
the ``capctl`` binary. It proves the SDK facade authenticates against the real
demo venue and reads accounts / a market / positions end-to-end. READ-ONLY: no
orders, no mutations.
"""

import asyncio
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e
if not os.environ.get("CAPCTL_E2E"):
    pytest.skip("set CAPCTL_E2E=1", allow_module_level=True)

REPO = Path(__file__).resolve().parents[2]
ENV_FILE = REPO / ".env"

# The CLI e2e passes the repo-root .env to a subprocess via CAP_ENV_FILE. The
# SDK runs IN-PROCESS, so point the in-process config at the same file (its
# resolution order is $CAP_ENV_FILE > ./.env > ~/.config/...). Setting it
# explicitly makes auth work regardless of the pytest working directory.
os.environ.setdefault("CAP_ENV_FILE", str(ENV_FILE))


def test_sdk_read_only_flow():
    from capital_cli.sdk import CapitalComApp, RiskPolicy

    async def _run():
        async with CapitalComApp() as app:
            assert isinstance(app.risk_policy, RiskPolicy)
            accounts = await app.accounts.list()
            assert "accounts" in accounts
            gold = await app.markets.get("GOLD")
            assert gold.get("instrument", {}).get("epic") == "GOLD"
            positions = await app.trading.list_positions()
            assert "positions" in positions

    asyncio.run(_run())


def test_sdk_risk_policy_reflects_config():
    from capital_cli.sdk import CapitalComApp

    async def _run():
        async with CapitalComApp() as app:
            rp = app.risk_policy
            assert rp.allow_trading == app.config.cap_allow_trading
            assert rp.max_position_size == app.config.cap_max_position_size
            assert isinstance(rp.allowed_epics, list)

    asyncio.run(_run())


def test_sdk_markets_and_prices():
    from capital_cli.sdk import CapitalComApp

    async def _run():
        async with CapitalComApp() as app:
            search = await app.markets.search("gold", limit=3)
            assert "markets" in search
            prices = await app.markets.prices("GOLD", resolution="HOUR", max_candles=5)
            assert prices.get("prices")

    asyncio.run(_run())


def test_sdk_trading_preview_only():
    from capital_cli.core.models import Direction, PreviewPositionRequest
    from capital_cli.sdk import CapitalComApp

    async def _run():
        async with CapitalComApp() as app:
            req = PreviewPositionRequest(epic="GOLD", direction=Direction.BUY, size=0.1)
            preview = await app.trading.preview_position(req)
            assert preview.preview_id
            assert isinstance(preview.all_checks_passed, bool)

    asyncio.run(_run())


def test_sdk_watchlist_lifecycle():
    from capital_cli.sdk import CapitalComApp

    async def _run():
        async with CapitalComApp() as app:
            created = await app.watchlists.create("capctl-sdk-e2e", confirm=True)
            wid = str(created.get("watchlistId") or created.get("id"))
            assert wid and wid != "None", created
            try:
                await app.watchlists.add_market(wid, "GOLD", confirm=True)
                got = await app.watchlists.get(wid)
                epics = [m.get("epic") for m in got.get("markets", [])]
                assert "GOLD" in epics, got
                await app.watchlists.remove_market(wid, "GOLD", confirm=True)
            finally:
                await app.watchlists.delete(wid, confirm=True)

    asyncio.run(_run())


def test_sdk_stream_prices_short():
    if os.environ.get("CAP_WS_ENABLED", "").lower() not in ("1", "true", "yes"):
        pytest.skip("set CAP_WS_ENABLED=true for the streaming SDK test")

    from capital_cli.core.models import PriceTick
    from capital_cli.sdk import CapitalComApp

    async def _run():
        async with CapitalComApp() as app:
            seen = 0
            async for tick in app.stream.prices(["BTCUSD"], duration=5):
                assert isinstance(tick, PriceTick)
                seen += 1
                if seen >= 1:
                    break

    asyncio.run(_run())


requires_sdk_trading = pytest.mark.skipif(
    os.environ.get("CAPCTL_E2E_TRADING") != "I_UNDERSTAND",
    reason="set CAPCTL_E2E_TRADING=I_UNDERSTAND to run the SDK trade lifecycle",
)


@requires_sdk_trading
def test_sdk_trade_lifecycle_leaves_account_flat():
    from capital_cli.core.models import Direction, PreviewPositionRequest
    from capital_cli.sdk import CapitalComApp

    async def _run():
        async with CapitalComApp() as app:
            mkt = await app.markets.get("BTCUSD")
            if mkt.get("snapshot", {}).get("marketStatus") != "TRADEABLE":
                pytest.skip("BTCUSD not TRADEABLE right now")
            req = PreviewPositionRequest(epic="BTCUSD", direction=Direction.BUY, size=0.001)
            preview = await app.trading.preview_position(req)
            assert preview.all_checks_passed, preview.checks
            result = await app.trading.execute_position(
                preview.preview_id, confirm=True, timeout_s=30
            )
            conf = result.get("confirmation") or {}
            assert conf.get("status") == "ACCEPTED", conf
            affected = conf.get("affectedDeals") or []
            deal_id = (affected[0].get("dealId") if affected else None) or conf.get("dealId")
            assert deal_id, conf
            try:
                close = await app.trading.close_position(deal_id, confirm=True, timeout_s=30)
                assert (close.get("confirmation") or {}).get("status") == "ACCEPTED", close
            finally:
                positions = await app.trading.list_positions()
                open_ids = [
                    p.get("position", {}).get("dealId") for p in positions.get("positions", [])
                ]
                assert deal_id not in open_ids, "SDK trade lifecycle left a position open"

    asyncio.run(_run())
