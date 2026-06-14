"""Reusable, presentation-free Capital.com domain services.

These compose the core/ primitives (config, http client, session, risk, state)
into per-domain operations with structured returns and no Typer/Rich. The CLI
and the SDK facade (capital_cli.sdk) both build on them.
"""

from .accounts import AccountService
from .markets import MarketService
from .trading import TradingService
from .watchlists import WatchlistService

__all__ = ["AccountService", "MarketService", "TradingService", "WatchlistService"]
