"""Shared e2e helpers: a non-asserting CLI runner (for negative exit-code checks
and env-override guard tests) and an SDK app builder that applies env overrides
with clean singleton isolation. Imported by the negative/positive e2e modules.

SECURITY: never reads or prints .env contents; only sets CAP_ENV_FILE to its path.
"""

from __future__ import annotations

import contextlib
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ENV_FILE = REPO / ".env"
STATE_FILE = REPO / ".pytest_cache" / "e2e_state.json"

# Identifiers guaranteed not to exist on the demo account — used for safe 404s.
BAD_EPIC = "CAPCTL_NO_SUCH_EPIC"
BAD_DEAL_ID = "00000000-0000-0000-0000-000000000000"
BAD_WATCHLIST_ID = "99999999"
BAD_NODE_ID = "99999999"
BAD_DEAL_REF = "capctl_no_such_ref"


@dataclass
class CliResult:
    code: int
    stdout: str
    stderr: str

    def json(self) -> dict:
        return json.loads(self.stdout) if self.stdout.strip() else {}

    def error(self) -> dict:
        """Parse the structured error object the CLI writes to STDERR under --json.

        Data goes to stdout; errors/notes go to stderr (see AGENTS.md). On error
        stdout is empty, so negative tests read the error code from here. Log lines
        may precede the JSON, so scan stderr lines from the end for the JSON object.
        """
        for line in reversed(self.stderr.strip().splitlines()):
            line = line.strip()
            if line.startswith("{"):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        return {}

    def error_code(self) -> str | None:
        return self.error().get("error", {}).get("code")


def run_cli(*args: str, env_overrides: dict[str, str] | None = None) -> CliResult:
    """Run `capctl --json <args>` and RETURN the result (never asserts the code).

    env_overrides lets a negative test force a guard (e.g. CAP_ALLOW_TRADING=false)
    without touching the account. Paces 1.2s to respect the 1 req/s login limit.
    """
    import os

    env = dict(os.environ, CAP_ENV_FILE=str(ENV_FILE), CAPCTL_STATE_FILE=str(STATE_FILE))
    if env_overrides:
        env.update(env_overrides)
    proc = subprocess.run(
        [sys.executable, "-m", "capital_cli", "--json", *args],
        capture_output=True,
        text=True,
        timeout=180,
        env=env,
        cwd=REPO,
    )
    time.sleep(1.2)
    return CliResult(proc.returncode, proc.stdout, proc.stderr)


def _reset_all_singletons() -> None:
    from capital_cli.core.config import reset_config
    from capital_cli.core.http_client import reset_client
    from capital_cli.core.rate_limit import reset_rate_limiter
    from capital_cli.core.risk import reset_risk_engine
    from capital_cli.core.session import reset_session_manager
    from capital_cli.core.state import reset_state_store

    reset_config()
    reset_client()
    reset_session_manager()
    reset_risk_engine()
    reset_rate_limiter()
    reset_state_store()


@contextlib.contextmanager
def sdk_app(env_overrides: dict[str, str] | None = None):
    """Yield a fresh CapitalComApp built from the real .env plus optional overrides.

    Overrides (e.g. CAP_ALLOW_TRADING=false, CAP_REQUIRE_EXPLICIT_CONFIRM=true) are
    applied to os.environ, singletons are rebuilt so services read them, and both
    are restored on exit. Use for SDK negative guard tests in-process.
    """
    import os

    os.environ["CAP_ENV_FILE"] = str(ENV_FILE)
    saved = {k: os.environ.get(k) for k in (env_overrides or {})}
    if env_overrides:
        os.environ.update(env_overrides)
    _reset_all_singletons()
    try:
        from capital_cli.sdk import CapitalComApp

        yield CapitalComApp()
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        _reset_all_singletons()
