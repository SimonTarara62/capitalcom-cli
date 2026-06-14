"""Global CLI state and resolution of global options into core config env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from capital_cli.cli.output import Output
from capital_cli.core.config import reset_config
from capital_cli.core.http_client import reset_client
from capital_cli.core.rate_limit import reset_rate_limiter
from capital_cli.core.risk import reset_risk_engine
from capital_cli.core.session import reset_session_manager
from capital_cli.core.state import reset_state_store


@dataclass
class AppState:
    """Carried on the Typer context object (ctx.obj) for every command."""

    out: Output


def init_state(
    *,
    json_mode: bool,
    env_file: Path | None,
    env: str | None,
    account: str | None,
    verbose: bool,
    no_color: bool = False,
    plain: bool = False,
) -> AppState:
    """
    Apply global options to the environment, then build shared state.

    Core config is read lazily via get_config(); setting env vars here (and
    resetting the cached config) guarantees commands see the overrides.
    """
    if env_file is not None:
        os.environ["CAP_ENV_FILE"] = str(env_file)
    if env is not None:
        os.environ["CAP_ENV"] = env
    if account is not None:
        os.environ["CAP_DEFAULT_ACCOUNT_ID"] = account
    if verbose:
        os.environ["CAP_LOG_LEVEL"] = "DEBUG"
    # Reset config AND every singleton that captured the old config, so global
    # overrides (e.g. switching --demo -> --live) take effect on the next call.
    reset_config()
    reset_client()
    reset_session_manager()
    reset_risk_engine()
    reset_rate_limiter()
    reset_state_store()
    return AppState(out=Output(json_mode=json_mode, no_color=no_color or None, plain=plain))
