"""Read-only snapshot of the risk limits in effect."""

from __future__ import annotations

from dataclasses import dataclass

from capital_cli.core.config import Config


@dataclass(frozen=True)
class RiskPolicy:
    allow_trading: bool
    allowed_epics: list[str]
    max_position_size: float
    max_working_order_size: float
    max_open_positions: int
    max_orders_per_day: int
    require_explicit_confirm: bool
    dry_run: bool

    def __init__(self, config: Config) -> None:
        object.__setattr__(self, "allow_trading", config.cap_allow_trading)
        object.__setattr__(self, "allowed_epics", list(config.allowed_epics_list))
        object.__setattr__(self, "max_position_size", config.cap_max_position_size)
        object.__setattr__(self, "max_working_order_size", config.cap_max_working_order_size)
        object.__setattr__(self, "max_open_positions", config.cap_max_open_positions)
        object.__setattr__(self, "max_orders_per_day", config.cap_max_orders_per_day)
        object.__setattr__(self, "require_explicit_confirm", config.cap_require_explicit_confirm)
        object.__setattr__(self, "dry_run", config.cap_dry_run)
