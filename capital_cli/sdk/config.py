"""Public configuration type for the Capital.com SDK (stable within 0.x)."""

from __future__ import annotations

from capital_cli.core.config import Config, get_config


class CapitalComConfig(Config):
    """Stable public alias of the internal settings model.

    Reads credentials and safety settings from environment / .env / CAP_*_CMD
    helpers exactly as the CLI does. Field names match the CAP_* env vars.
    """

    @classmethod
    def from_env(cls) -> CapitalComConfig:
        base = get_config()
        return cls.model_validate(base.model_dump())
