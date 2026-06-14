"""SDK positive e2e for endpoints not in test_sdk_e2e.py — the in-process path an
MCP server / dashboard uses. conftest._use_real_env points config at the real
.env. Read-only tests run on CAPCTL_E2E; trading lifecycles gate on
CAPCTL_E2E_TRADING and leave the account flat. Opt-in via CAPCTL_E2E=1.
"""

import asyncio
import os

import pytest

pytestmark = pytest.mark.e2e
if not os.environ.get("CAPCTL_E2E"):
    pytest.skip("set CAPCTL_E2E=1", allow_module_level=True)

_TRADING_OK = os.environ.get("CAPCTL_E2E_TRADING") == "I_UNDERSTAND"
requires_trading = pytest.mark.skipif(
    not _TRADING_OK, reason="set CAPCTL_E2E_TRADING=I_UNDERSTAND"
)
EPIC = "BTCUSD"


def test_sdk_session_ping_switch_logout():
    from capital_cli.sdk import CapitalComApp

    async def _run():
        async with CapitalComApp() as app:
            ping = await app.session.ping()
            assert isinstance(ping, dict)
            accounts = await app.accounts.list()
            ids = [a.get("accountId") for a in accounts.get("accounts", [])]
            assert ids, accounts
            await app.session.switch_account(ids[0])
            assert app.session.account_id == ids[0]
        async with CapitalComApp() as app2:
            await app2.session.logout()

    asyncio.run(_run())


def test_sdk_account_prefs_and_history():
    from capital_cli.sdk import CapitalComApp

    async def _run():
        async with CapitalComApp() as app:
            prefs = await app.accounts.get_preferences()
            assert "leverages" in prefs or "hedgingMode" in prefs, prefs
            act = await app.accounts.history_activity(last_period=3600)
            assert isinstance(act, dict)
            txn = await app.accounts.history_transactions(last_period=3600)
            assert isinstance(txn, dict)

    asyncio.run(_run())


def test_sdk_market_sentiment_and_navigation():
    from capital_cli.sdk import CapitalComApp

    async def _run():
        async with CapitalComApp() as app:
            sent = await app.markets.sentiment([EPIC])
            assert isinstance(sent, dict)
            root = await app.markets.navigation_root()
            assert root.get("nodes"), root
            node = await app.markets.navigation_node(str(root["nodes"][0]["id"]), limit=5)
            assert ("nodes" in node) or ("markets" in node), node

    asyncio.run(_run())


def test_sdk_orders_list():
    from capital_cli.sdk import CapitalComApp

    async def _run():
        async with CapitalComApp() as app:
            orders = await app.trading.list_orders()
            assert "workingOrders" in orders, orders

    asyncio.run(_run())


def test_sdk_watchlist_list():
    from capital_cli.sdk import CapitalComApp

    async def _run():
        async with CapitalComApp() as app:
            wls = await app.watchlists.list()
            assert isinstance(wls, dict)

    asyncio.run(_run())


@requires_trading
def test_sdk_prefs_roundtrip_and_topup():
    from capital_cli.sdk import CapitalComApp

    async def _run():
        async with CapitalComApp() as app:
            prefs = await app.accounts.get_preferences()
            lev = prefs.get("leverages", {})
            asset, value = next(iter(lev.items())) if lev else ("CRYPTOCURRENCIES", 2)
            updated = await app.accounts.set_preferences(
                leverages={asset: int(value)}, confirm=True
            )
            assert isinstance(updated, dict)
            topped = await app.accounts.demo_topup(1.0, confirm=True)
            assert isinstance(topped, dict)

    asyncio.run(_run())


@requires_trading
def test_sdk_position_get_amend_close():
    from capital_cli.core.models import Direction, PreviewPositionRequest
    from capital_cli.sdk import CapitalComApp

    async def _run():
        async with CapitalComApp() as app:
            market = await app.markets.get(EPIC)
            if market.get("snapshot", {}).get("marketStatus") != "TRADEABLE":
                pytest.skip(f"{EPIC} not TRADEABLE")
            preview = await app.trading.preview_position(
                PreviewPositionRequest(epic=EPIC, direction=Direction.BUY, size=0.001)
            )
            assert preview.all_checks_passed, preview.checks
            opened = await app.trading.execute_position(
                preview.preview_id, confirm=True, timeout_s=30
            )
            conf = opened.get("confirmation") or {}
            affected = conf.get("affectedDeals") or []
            deal_id = (affected[0].get("dealId") if affected else None) or conf.get("dealId")
            assert deal_id, opened
            try:
                got = await app.trading.get_position(deal_id)
                assert got.get("position", {}).get("dealId") == deal_id, got
                bid = float(market["snapshot"]["bid"])
                amended = await app.trading.amend_position(
                    deal_id,
                    body={"stopLevel": round(bid * 0.5, 2)},
                    confirm=True,
                    timeout_s=30,
                )
                assert (amended.get("confirmation") or {}).get("status") in {
                    "ACCEPTED", "TIMEOUT",
                }, amended
            finally:
                await app.trading.close_position(deal_id, confirm=True, timeout_s=30)
                positions = await app.trading.list_positions()
                open_ids = [
                    p.get("position", {}).get("dealId") for p in positions.get("positions", [])
                ]
                assert deal_id not in open_ids, "SDK left a position open"

    asyncio.run(_run())


@requires_trading
def test_sdk_working_order_lifecycle_and_confirm():
    from capital_cli.core.models import Direction, PreviewWorkingOrderRequest, WorkingOrderType
    from capital_cli.sdk import CapitalComApp
    from capital_cli.services.confirmations import get_confirmation

    async def _run():
        async with CapitalComApp() as app:
            market = await app.markets.get(EPIC)
            if market.get("snapshot", {}).get("marketStatus") != "TRADEABLE":
                pytest.skip(f"{EPIC} not TRADEABLE")
            bid = float(market["snapshot"]["bid"])
            far_below = round(bid * 0.5, 2)
            preview = await app.trading.preview_working_order(
                PreviewWorkingOrderRequest(
                    epic=EPIC, direction=Direction.BUY, type=WorkingOrderType.LIMIT,
                    level=far_below, size=0.001,
                )
            )
            assert preview.all_checks_passed, preview.checks
            created = await app.trading.execute_working_order(
                preview.preview_id, confirm=True, timeout_s=30
            )
            deal_ref = created.get("dealReference")
            assert deal_ref, created
            deal_id = None
            try:
                conf = await get_confirmation(deal_ref)
                assert isinstance(conf, dict)
                orders = await app.trading.list_orders()
                for o in orders.get("workingOrders", []):
                    data = o.get("workingOrderData", {})
                    if data.get("epic") == EPIC:
                        deal_id = data.get("dealId")
                        break
                assert deal_id, orders
                amended = await app.trading.amend_order(
                    deal_id, body={"level": round(far_below * 0.99, 2)},
                    confirm=True, timeout_s=30,
                )
                assert isinstance(amended, dict)
            finally:
                if deal_id:
                    await app.trading.cancel_order(deal_id, confirm=True, timeout_s=30)

    asyncio.run(_run())


def _ws_enabled() -> bool:
    from capital_cli.sdk import CapitalComApp

    return CapitalComApp().config.cap_ws_enabled


def test_sdk_stream_candles_short():
    if not _ws_enabled():
        pytest.skip("streaming disabled")
    from capital_cli.core.models import OHLCBar
    from capital_cli.sdk import CapitalComApp

    async def _run():
        async with CapitalComApp() as app:
            async for bar in app.stream.candles([EPIC], ["MINUTE"], duration=10):
                assert isinstance(bar, OHLCBar)
                break

    asyncio.run(_run())


def test_sdk_stream_alerts_short():
    if not _ws_enabled():
        pytest.skip("streaming disabled")
    from capital_cli.sdk import CapitalComApp

    async def _run():
        async with CapitalComApp() as app:
            seen = 0
            async for _alert in app.stream.alerts(EPIC, 1.0, direction="BELOW", duration=5):
                seen += 1
                break
            assert seen >= 0

    asyncio.run(_run())


def test_sdk_stream_portfolio_short():
    if not _ws_enabled():
        pytest.skip("streaming disabled")
    from capital_cli.core.models import PriceTick
    from capital_cli.sdk import CapitalComApp

    async def _run():
        async with CapitalComApp() as app:
            async for tick in app.stream.portfolio([EPIC], duration=5):
                assert isinstance(tick, PriceTick)
                break

    asyncio.run(_run())
