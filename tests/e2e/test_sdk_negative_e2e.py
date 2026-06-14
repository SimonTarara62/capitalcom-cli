"""SDK negative e2e: every SDK-exposed method's failure path, in-process, without
mutating the account. Bad ids raise broker errors; invalid models raise
ValidationError; guard overrides raise typed errors before any HTTP; bad creds
raise auth errors. Opt-in via CAPCTL_E2E=1.
"""

import asyncio
import os

import pytest

from tests.e2e._helpers import (
    BAD_DEAL_ID,
    BAD_DEAL_REF,
    BAD_EPIC,
    BAD_NODE_ID,
    BAD_WATCHLIST_ID,
    sdk_app,
)

pytestmark = pytest.mark.e2e
if not os.environ.get("CAPCTL_E2E"):
    pytest.skip("set CAPCTL_E2E=1", allow_module_level=True)

EPIC = "BTCUSD"
_BAD_CREDS = {"CAP_API_PASSWORD": "definitely-wrong-password", "CAP_PERSIST_SESSION": "false"}


@pytest.mark.parametrize(
    "endpoint_id",
    ["market.get", "market.prices", "market.nav_node", "position.get",
     "watchlist.get", "trade.confirm"],
)
def test_sdk_bad_identifier_raises(endpoint_id):
    from capital_cli.core.errors import CapitalCLIError
    from capital_cli.sdk import CapitalComApp
    from capital_cli.services.confirmations import get_confirmation

    async def _run():
        async with CapitalComApp() as app:
            calls = {
                "market.get": app.markets.get(BAD_EPIC),
                "market.prices": app.markets.prices(BAD_EPIC),
                "market.nav_node": app.markets.navigation_node(BAD_NODE_ID),
                "position.get": app.trading.get_position(BAD_DEAL_ID),
                "watchlist.get": app.watchlists.get(BAD_WATCHLIST_ID),
                "trade.confirm": get_confirmation(BAD_DEAL_REF),
            }
            with pytest.raises(CapitalCLIError):
                await calls[endpoint_id]

    asyncio.run(_run())


def test_sdk_preview_position_invalid_size():
    import pydantic

    from capital_cli.core.models import Direction, PreviewPositionRequest

    with pytest.raises((pydantic.ValidationError, ValueError)):
        PreviewPositionRequest(epic="GOLD", direction=Direction.BUY, size=-1)


def test_sdk_preview_order_invalid():
    import pydantic

    from capital_cli.core.models import Direction, PreviewWorkingOrderRequest, WorkingOrderType

    with pytest.raises((pydantic.ValidationError, ValueError)):
        PreviewWorkingOrderRequest(
            epic="GOLD", direction=Direction.BUY, type=WorkingOrderType.LIMIT,
            level=1.0, size=-5,
        )


def test_sdk_execute_position_trading_disabled():
    from capital_cli.core.errors import TradingDisabledError

    async def _run(app):
        async with app:
            with pytest.raises(TradingDisabledError):
                await app.trading.execute_position("no-preview", confirm=True)

    with sdk_app(env_overrides={"CAP_ALLOW_TRADING": "false"}) as app:
        asyncio.run(_run(app))


def test_sdk_execute_order_trading_disabled():
    from capital_cli.core.errors import TradingDisabledError

    async def _run(app):
        async with app:
            with pytest.raises(TradingDisabledError):
                await app.trading.execute_working_order("no-preview", confirm=True)

    with sdk_app(env_overrides={"CAP_ALLOW_TRADING": "false"}) as app:
        asyncio.run(_run(app))


def test_sdk_close_trading_disabled():
    from capital_cli.core.errors import TradingDisabledError

    async def _run(app):
        async with app:
            with pytest.raises(TradingDisabledError):
                await app.trading.close_position(BAD_DEAL_ID, confirm=True)

    with sdk_app(env_overrides={"CAP_ALLOW_TRADING": "false"}) as app:
        asyncio.run(_run(app))


@pytest.mark.parametrize("endpoint_id", ["order.cancel", "position.amend", "order.amend"])
def test_sdk_trade_mutations_trading_disabled(endpoint_id):
    from capital_cli.core.errors import TradingDisabledError

    async def _run(app):
        async with app:
            calls = {
                "order.cancel": app.trading.cancel_order(BAD_DEAL_ID, confirm=True),
                "position.amend": app.trading.amend_position(BAD_DEAL_ID, body={"stopLevel": 1}, confirm=True),
                "order.amend": app.trading.amend_order(BAD_DEAL_ID, body={"level": 1}, confirm=True),
            }
            with pytest.raises(TradingDisabledError):
                await calls[endpoint_id]

    with sdk_app(env_overrides={"CAP_ALLOW_TRADING": "false"}) as app:
        asyncio.run(_run(app))


@pytest.mark.parametrize(
    "endpoint_id",
    ["watchlist.create", "watchlist.add", "watchlist.remove", "watchlist.delete",
     "account.prefs_set", "account.topup"],
)
def test_sdk_nontrade_mutations_require_confirm(endpoint_id):
    from capital_cli.core.errors import ConfirmRequiredError

    async def _run(app):
        async with app:
            calls = {
                "watchlist.create": app.watchlists.create("capctl-neg", confirm=False),
                "watchlist.add": app.watchlists.add_market(BAD_WATCHLIST_ID, "GOLD", confirm=False),
                "watchlist.remove": app.watchlists.remove_market(BAD_WATCHLIST_ID, "GOLD", confirm=False),
                "watchlist.delete": app.watchlists.delete(BAD_WATCHLIST_ID, confirm=False),
                "account.prefs_set": app.accounts.set_preferences(leverages={"CRYPTOCURRENCIES": 2}, confirm=False),
                "account.topup": app.accounts.demo_topup(100.0, confirm=False),
            }
            with pytest.raises(ConfirmRequiredError):
                await calls[endpoint_id]

    with sdk_app(env_overrides={"CAP_REQUIRE_EXPLICIT_CONFIRM": "true"}) as app:
        asyncio.run(_run(app))


@pytest.mark.parametrize(
    "endpoint_id",
    ["session.ping", "session.switch", "session.logout", "session.login",
     "account.list", "account.prefs_get", "account.history_activity",
     "account.history_transactions", "market.search", "market.sentiment",
     "market.nav_root", "position.list", "order.list", "watchlist.list"],
)
def test_sdk_auth_failure_raises(endpoint_id):
    from capital_cli.core.errors import CapitalCLIError

    async def _run(app):
        calls = {
            "session.login": lambda: app.session.login(force=True),
            "session.ping": lambda: app.session.ping(),
            "session.switch": lambda: app.session.switch_account("x"),
            "session.logout": lambda: app.session.login(force=True),
            "account.list": lambda: app.accounts.list(),
            "account.prefs_get": lambda: app.accounts.get_preferences(),
            "account.history_activity": lambda: app.accounts.history_activity(),
            "account.history_transactions": lambda: app.accounts.history_transactions(),
            "market.search": lambda: app.markets.search("gold"),
            "market.sentiment": lambda: app.markets.sentiment(["GOLD"]),
            "market.nav_root": lambda: app.markets.navigation_root(),
            "position.list": lambda: app.trading.list_positions(),
            "order.list": lambda: app.trading.list_orders(),
            "watchlist.list": lambda: app.watchlists.list(),
        }
        with pytest.raises(CapitalCLIError):
            await calls[endpoint_id]()

    with sdk_app(env_overrides=_BAD_CREDS) as app:
        asyncio.run(_run(app))


@pytest.mark.parametrize(
    "endpoint_id", ["stream.prices", "stream.candles", "stream.portfolio", "stream.alerts"]
)
def test_sdk_stream_auth_failure(endpoint_id):
    from capital_cli.core.errors import CapitalCLIError

    async def _run(app):
        gens = {
            "stream.prices": app.stream.prices([EPIC], duration=2),
            "stream.candles": app.stream.candles([EPIC], ["MINUTE"], duration=2),
            "stream.portfolio": app.stream.portfolio([EPIC], duration=2),
            "stream.alerts": app.stream.alerts(EPIC, 1.0, duration=2),
        }
        with pytest.raises(CapitalCLIError):
            async for _ in gens[endpoint_id]:
                break

    with sdk_app(env_overrides=_BAD_CREDS) as app:
        asyncio.run(_run(app))
