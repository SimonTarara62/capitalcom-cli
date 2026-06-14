# AGENTS.md

Guidance for AI coding agents working in this repository. Humans: start with
[README.md](README.md) and [CONTRIBUTING.md](CONTRIBUTING.md).

## What this is

`capctl` (distribution name `capitalcom-cli`) is a command-line client for the
Capital.com Open API, built with Typer + Rich. The CLI is the first-class
surface, but there is also an **experimental** SDK layer at `capital_cli.sdk`
(exporting `CapitalComApp`, `CapitalComConfig`, `RiskPolicy`) that embeds the
same tested broker engine in your own Python — see [docs/sdk.md](docs/sdk.md).
The SDK import paths and the `capital_cli.core.models` pydantic models are
documented and intended-stable but may shift between 0.x minors until 1.0. The
`capital_cli.core.*` internals remain **private** — depend on
`capital_cli.sdk` / `capital_cli.services`, not on `core`.

## Setup & commands

```bash
pip install -e ".[dev]"          # install with dev tooling
pytest -q                        # offline test suite (no network/credentials)
ruff check capital_cli tests     # lint
ruff format capital_cli tests    # format
mypy capital_cli                 # type-check the whole package
typer capital_cli.cli.app utils docs --name capctl --output docs/CLI.md  # regen CLI reference
```

All of these are wrapped in the Makefile: `make test`, `make lint`, `make fmt`,
`make typecheck`, `make docs`, and `make check` (lint + typecheck + test).

The opt-in end-to-end suite hits the real Capital.com **demo** API and needs
credentials:

```bash
CAPCTL_E2E=1 pytest tests/e2e -m e2e -v
```

## Project structure

- `capital_cli/core/` — low-level primitives: config, HTTP client, session,
  rate limiter, risk engine, models, WebSocket, audit, state. **All safety
  rules live in `core/risk.py`.**
- `capital_cli/services/` — presentation-free domain services (markets,
  accounts, watchlists, trading, streaming, confirmations) composing `core`;
  the reusable broker engine.
- `capital_cli/sdk/` — the experimental public facade (`CapitalComApp`,
  `CapitalComConfig`, `RiskPolicy`).
- `capital_cli/cli/` — thin Typer wrappers, one app per command group;
  Rich/JSON rendering in `cli/output.py`; the async→exit-code runner in
  `cli/runner.py`.
- `tests/` — offline unit tests; `tests/e2e/` — opt-in live-demo tests.
- The `cli/` layer never calls the broker API directly: parse args → call a
  service → render the result (it goes through `services`, not the broker).

## Tech stack

Python 3.10+ · Typer ≥0.12 · Rich ≥13.7 · httpx ≥0.27 · pydantic v2 +
pydantic-settings · websockets ≥12.

## Conventions

- TDD: write the failing test first, then the minimal code. The offline suite
  mocks HTTP/WebSocket — no network.
- Keep `cli/` thin; put logic and **all** risk validation in `core/`.
- Every command supports `--json`. Data goes to **stdout**; logs, errors, notes,
  prompts, and banners go to **stderr**.
- Branch → PR → CI. CI (ruff + mypy + pytest on 3.10/3.11/3.12) must pass.

## Boundaries — IMPORTANT (this is a trading tool)

- **Default to the demo environment (`CAP_ENV=demo`). Never enable
  `CAP_ALLOW_TRADING` in tests and never place live orders.**
- **Never hardcode or commit API keys, credentials, or `.env`.** Credentials
  come only from environment variables, a git-ignored `.env`, or a `CAP_*_CMD`
  credential-exec helper. An LLM sharing this shell can read any secret the CLI
  can use — secrecy isn't achievable in that setting; rely on least-privilege
  keys + the safety layer. See [SECURITY.md](SECURITY.md#using-capctl-with-ai-agents--llms).
- Trade execution is two-phase: always `trade preview-*` before
  `trade execute-*`. Never add a path that executes without a valid preview.
- **A `{"status": "TIMEOUT"}` confirmation is ambiguous** — the order may have
  landed. There is no broker idempotency key, so never blindly re-run
  `execute-*`/`close`/`cancel`/`amend-*` on TIMEOUT. Reconcile first via
  `trade positions` / `trade orders`, then retry only if the order is absent.
  See [docs/scripting.md](docs/scripting.md#safe-retries--ambiguous-confirmations).
- Do not weaken the risk engine (`core/risk.py`) or the trade-size validation to
  make a test pass.

## Related interfaces

- A sibling **MCP server** exposes the same Capital.com API as agent tools; this
  CLI is the terminal/scripting/CI surface. `--json` makes it agent-usable too.
  Such a sibling should import `capital_cli.sdk` directly (the
  `CapitalComApp` facade + services) rather than subprocessing the `capctl`
  binary — same tested engine, no process/parse overhead. See
  [docs/sdk.md](docs/sdk.md).
