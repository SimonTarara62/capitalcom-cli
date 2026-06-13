"""Emit a loud banner before actions that hit the live (real-money) account."""

from __future__ import annotations

from capital_cli.cli.output import Output
from capital_cli.core.config import CapEnv, get_config


def warn_if_live(out: Output) -> None:
    """Print a live-account banner to stderr when the environment is live."""
    if get_config().cap_env == CapEnv.LIVE:
        out.banner_live()
