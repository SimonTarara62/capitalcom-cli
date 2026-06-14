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
