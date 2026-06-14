"""CapitalComApp — the SDK facade wiring config + services + risk policy.

EXPERIMENTAL (0.x): one app per process. The underlying services use
process-global singletons, so constructing a second CapitalComApp with a
different config in the same process is not supported yet.
"""

from __future__ import annotations

from types import TracebackType

from capital_cli.core.config import get_config
from capital_cli.core.session import get_session_manager
from capital_cli.sdk.config import CapitalComConfig
from capital_cli.sdk.risk_policy import RiskPolicy
from capital_cli.services.accounts import AccountService
from capital_cli.services.markets import MarketService
from capital_cli.services.streaming import StreamService
from capital_cli.services.trading import TradingService
from capital_cli.services.watchlists import WatchlistService


class CapitalComApp:
    def __init__(self, config: CapitalComConfig | None = None) -> None:
        self.config = config or CapitalComConfig.from_env()
        self.session = get_session_manager()
        self.markets = MarketService()
        self.accounts = AccountService()
        self.watchlists = WatchlistService()
        self.trading = TradingService()
        self.stream = StreamService()
        self.risk_policy = RiskPolicy(get_config())

    async def __aenter__(self) -> CapitalComApp:
        await self.session.ensure_logged_in()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        # Close the shared HTTP client (CapitalClient.close()) so sockets are
        # released. We deliberately do NOT logout here — the cached session
        # (issue #10) must persist for back-to-back reuse.
        from capital_cli.core.http_client import get_client

        client = get_client()
        close = getattr(client, "close", None)
        if callable(close):
            await close()
