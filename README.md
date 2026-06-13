# capctl — Capital.com CLI

A fast, scriptable command-line client for the [Capital.com](https://capital.com) Open API, built with Typer and Rich.

Browse markets, manage accounts and watchlists, preview and execute trades behind multiple safety guardrails, and stream real-time prices — from your terminal, in human-readable tables or raw JSON for automation.

[![CI](https://github.com/SimonTarara62/capitalcom-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/SimonTarara62/capitalcom-cli/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Release](https://img.shields.io/github/v/release/SimonTarara62/capitalcom-cli?sort=semver)](https://github.com/SimonTarara62/capitalcom-cli/releases)

```text
$ capctl market search "gold"
Markets
┏━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ epic   ┃ instrumentName ┃ bid     ┃ offer   ┃ marketStatus ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ GOLD   │ Gold           │ 2331.05 │ 2331.35 │ TRADEABLE    │
└────────┴────────────────┴─────────┴─────────┴──────────────┘
```

> **New to this?** The [getting-started guide](docs/getting-started.md) walks you from zero (no account, no API key) to your first practice trade on a demo account. Hit a problem? See [troubleshooting](docs/troubleshooting.md).

> **Risk disclaimer:** This is an unofficial tool, not affiliated with or endorsed by Capital.com, and nothing here is financial advice. CFD trading carries a high risk of losing money. The CLI defaults to the **demo** environment and disables trading until you explicitly opt in — keep it that way until you know exactly what you're doing. Use at your own risk.

## Why capctl?

The Capital.com web platform is built for clicking; `capctl` is built for **repeating, scripting, and automating**. Anything you do through it can be put in a shell script, a cron job, or a pipeline — with machine-readable JSON output and exit codes you can branch on. And unlike ad-hoc API scripts, every action goes through the same safety layer: demo by default, trading off by default, an explicit market allowlist, size and daily-order limits, and a two-phase preview→execute flow that makes "oops, wrong size" structurally hard.

**Who gets value from it:**

- **Traders who live in the terminal** — check positions, P&L, and orders in seconds without opening a browser; set a price alert and keep working.
- **People learning to trade** — practice the full lifecycle (research → preview → execute → manage → close) on a demo account with virtual money, with guardrails on from the start. The [getting-started guide](docs/getting-started.md) assumes zero experience.
- **Developers building on the Capital.com API** — `--json` output mirrors the real API responses, so `capctl` doubles as an interactive API explorer while you build your own integration; the risk-engine pattern (allowlist, limits, preview/confirm) is reusable as a reference.
- **Data and automation folks** — pull historical OHLC candles into CSV/pandas, log portfolio snapshots from cron, monitor markets from scripts, wire alerts into anything that can run a shell command.

See [practical use cases](docs/use-cases.md) for worked, copy-pasteable scenarios.

**Scope:** `capctl` is a command-line application, not a stable Python SDK — the
internal `capital_cli.*` modules may change between releases without notice. It is
also short-lived: each command runs as its own process and may create its own API
session. `capctl session login` is mainly a connectivity/account check; session
tokens are not persisted between separate invocations.

## Features

- **Six command groups** covering the main Capital.com Open API workflows — `session`, `market`, `account`, `trade`, `watchlist`, `stream` (see the [API coverage table](docs/api-coverage.md))
- **Safety-first trading** — trading is off by default; enabling it requires an explicit EPIC allowlist, every execution goes through a two-phase *preview → execute* flow with risk checks, and mutating commands require `--yes`
- **`--json` everywhere** — every command can emit raw JSON for piping into `jq`, scripts, or CI jobs
- **Distinct exit codes per failure class** — scripts can branch on *why* a command failed (auth vs. risk-block vs. upstream error)
- **Real-time streaming** — live price tables, price-level alerts, and portfolio snapshots over WebSocket
- **Demo and live environments** — defaults to demo; live requires explicit opt-in
- **Built-in rate limiting** — client-side token buckets respect Capital.com's 10 req/s global, 1 req/s session, and trading-burst limits

## Installation

Requires Python 3.10+.

**One-line install (recommended)** — isolated, global `capctl` command, no clone:

```bash
pipx install git+https://github.com/SimonTarara62/capitalcom-cli.git
```

Using [uv](https://docs.astral.sh/uv/) instead of pipx:

```bash
uv tool install git+https://github.com/SimonTarara62/capitalcom-cli.git
```

Plain pip (into the active environment):

```bash
pip install git+https://github.com/SimonTarara62/capitalcom-cli.git
```

**From a clone (for development):**

```bash
git clone https://github.com/SimonTarara62/capitalcom-cli.git
cd capitalcom-cli
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

Verify and enable shell completion (bash/zsh/fish, provided by Typer):

```bash
capctl --version
capctl --install-completion
```

### Shell completion

capctl ships completion for bash, zsh, and fish (via Typer):

```bash
capctl --install-completion        # install for your current shell
capctl --show-completion           # print the script (to inspect or source manually)
```

Restart your shell (or `source` your rc file) after installing.

## Configuration

Generate an API key in the Capital.com platform under **Settings → API integrations**, then:

```bash
cp .env.example .env
# edit .env and fill in CAP_API_KEY, CAP_IDENTIFIER, CAP_API_PASSWORD
```

Credentials are resolved in this order:

1. `--env-file PATH` flag
2. `$CAP_ENV_FILE` environment variable
3. `./.env` in the current directory
4. `~/.config/capital-cli/.env`

All settings (one `CAP_*` variable each) and their defaults:

| Variable | Default | Purpose |
|----------|---------|---------|
| `CAP_ENV` | `demo` | `demo` or `live` |
| `CAP_API_KEY` | — | API key (required) |
| `CAP_IDENTIFIER` | — | Login email (required) |
| `CAP_API_PASSWORD` | — | API-key custom password (required) |
| `CAP_ALLOW_TRADING` | `false` | Master switch for all trade execution |
| `CAP_ALLOWED_EPICS` | (empty) | Comma-separated allowlist, or `ALL` |
| `CAP_MAX_POSITION_SIZE` | `1.0` | Per-trade size ceiling |
| `CAP_MAX_WORKING_ORDER_SIZE` | `1.0` | Per-order size ceiling |
| `CAP_MAX_OPEN_POSITIONS` | `3` | Open-position cap |
| `CAP_MAX_ORDERS_PER_DAY` | `20` | Daily order counter |
| `CAP_REQUIRE_EXPLICIT_CONFIRM` | `true` | Mutations need `--yes` |
| `CAP_DRY_RUN` | `false` | Block all executions regardless of other flags |
| `CAP_DEFAULT_ACCOUNT_ID` | (none) | Account selected after login |
| `CAP_HTTP_TIMEOUT_S` | `15` | HTTP timeout |
| `CAP_LOG_LEVEL` | `WARNING` | `DEBUG` … `CRITICAL` |
| `CAP_WS_ENABLED` | `false` | Required for `capctl stream …` |

Trade previews and the daily order counter persist between commands in
`~/.config/capital-cli/state.json` (override with `CAPCTL_STATE_FILE`).

## Global flags

These go **before** the command group:

| Flag | Purpose |
|------|---------|
| `--json` | Emit raw JSON instead of tables |
| `--plain` | Tab-delimited rows for piping (no boxes/colors) |
| `--no-color` | Disable colored output (also honors `NO_COLOR`) |
| `--demo` / `--live` | Force environment for this invocation |
| `--env-file PATH` | Use a specific credentials file |
| `--account ID`, `-a` | Use a specific account |
| `--verbose`, `-v` | Debug logging (incl. per-command timing) |
| `--version` | Print version and exit |

## Command reference

### Session

```bash
capctl session status            # local session state (no network call)
capctl session details           # server-side session info (client/account ids, timezone)
capctl session time              # broker server time (no auth)
capctl session encryption-key    # API encryption key for encrypted-password login
capctl session login [--force] [--account ID]
capctl session ping              # keep the session alive
capctl session switch ACCOUNT_ID
capctl session logout
```

Note: commands that need authentication log in automatically; an explicit `login` is rarely required.

### Market data

```bash
capctl market search "bitcoin" [--limit 20]
capctl market search --epics GOLD,SILVER
capctl market get GOLD                          # details + dealing rules
capctl market nav-root                          # top-level categories
capctl market nav-node NODE_ID                  # drill into a category
capctl market prices GOLD --resolution HOUR --max 48
capctl market sentiment GOLD                    # client long/short %
capctl market sentiment GOLD,SILVER,BTCUSD      # batch sentiment for several markets
capctl market nav-node NODE_ID --limit 50       # cap the number of children returned
```

Price resolutions: `MINUTE`, `MINUTE_5`, `MINUTE_15`, `MINUTE_30`, `HOUR`, `HOUR_4`, `DAY`, `WEEK`.

### Account

```bash
capctl account list
capctl account prefs-get
capctl account prefs-set --hedging --yes        # risk-gated
capctl account prefs-set --leverage CRYPTOCURRENCIES=2 --leverage CURRENCIES=20 --yes
capctl account history-activity --last 3600
capctl account history-transactions --last 86400 [--type DEPOSIT]
capctl account topup 1000 --yes                 # demo environment only
```

### Trading

Read-only:

```bash
capctl trade positions
capctl trade position DEAL_ID
capctl trade orders
capctl trade confirm DEAL_REFERENCE [--wait --timeout 30]
```

Two-phase execution — preview first (validates against the risk policy and broker dealing rules, **creates nothing**), then execute with the returned `preview_id`:

```bash
capctl trade preview-position GOLD BUY 0.5 --stop-distance 10 --profit-distance 20
# → returns preview_id, risk-check table, estimated entry

capctl trade execute-position <preview_id> --yes
```

Working orders follow the same shape:

```bash
capctl trade preview-order GOLD BUY LIMIT 2300 0.5 --good-till 2026-07-01T00:00:00
capctl trade execute-order <preview_id> --yes
```

Closing and cancelling:

```bash
capctl trade close DEAL_ID --yes
capctl trade cancel DEAL_ID --yes
```

Amending an open position or a pending order (stops, limits, level, expiry):

```bash
capctl trade amend-position DEAL_ID --stop-level 2300 --profit-level 2450 --yes
capctl trade amend-order DEAL_ID --level 2310 --good-till 2026-08-01T00:00:00 --yes
```

Previews expire after 120 seconds. Execution commands wait for broker confirmation by default (`--no-wait` to skip; `--timeout` to tune).

### Watchlists

```bash
capctl watchlist list
capctl watchlist get WATCHLIST_ID
capctl watchlist create "Metals" --yes
capctl watchlist add WATCHLIST_ID GOLD --yes
capctl watchlist remove WATCHLIST_ID GOLD --yes
capctl watchlist delete WATCHLIST_ID --yes
```

### Streaming (requires `CAP_WS_ENABLED=true`)

```bash
capctl stream prices GOLD,SILVER,EURUSD --duration 120     # live updating table
capctl stream candles GOLD,BTCUSD --resolution MINUTE_5         # live OHLC candlesticks
capctl stream candles BTCUSD --resolution HOUR --type heikin-ashi
capctl stream alerts GOLD 2400 --direction ABOVE           # beep when crossed
capctl stream portfolio --duration 300 --interval 5        # snapshots for open positions
```

Streams stop after `--duration` seconds or Ctrl-C. Capital.com allows at most 40 concurrent EPIC subscriptions.

## Use cases

Quick recipes below; for fuller worked scenarios (paper-trading practice, data analysis, cron monitoring, safe automation, API exploration) see [docs/use-cases.md](docs/use-cases.md).

**Morning check — one screen of context:**

```bash
capctl account list && capctl trade positions && capctl trade orders
```

**Scripting with `--json` and `jq` — extract the GOLD bid:**

```bash
capctl --json market search --epics GOLD | jq -r '.markets[0].bid'
```

**Export 200 daily candles to a CSV:**

```bash
capctl --json market prices GOLD --resolution DAY --max 200 \
  | jq -r '.prices[] | [.snapshotTime, .openPrice.bid, .highPrice.bid, .lowPrice.bid, .closePrice.bid] | @csv' \
  > gold_daily.csv
```

**Safe trade in the demo environment, end to end:**

```bash
# .env: CAP_ENV=demo, CAP_ALLOW_TRADING=true, CAP_ALLOWED_EPICS=GOLD
PREVIEW=$(capctl --json trade preview-position GOLD BUY 0.5 --stop-distance 15 | jq -r .preview_id)
capctl trade execute-position "$PREVIEW" --yes
capctl trade positions
```

**Branch on failure class in a script:**

```bash
capctl --json trade execute-position "$PREVIEW" --yes
case $? in
  0) echo "filled" ;;
  4) echo "blocked by safety policy (trading disabled / confirm / risk limit)" ;;
  5) echo "auth problem — check credentials" ;;
  7) echo "broker/upstream error — retry later" ;;
esac
```

**Watch for a breakout while you work:**

```bash
capctl stream alerts BTCUSD 75000 --direction ABOVE --duration 3600
```

**Cron-driven snapshot (JSON logs, no tables):**

```bash
*/15 * * * * capctl --json trade positions >> ~/logs/positions.jsonl 2>&1
```

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Unexpected internal error |
| 2 | Invalid input (bad parameter or failed validation) |
| 3 | Configuration error (missing/invalid credentials) |
| 4 | Safety policy block (trading disabled, dry-run, confirm required, EPIC not allowed, risk limit) |
| 5 | Authentication/session failure |
| 6 | Local rate limit exceeded |
| 7 | Broker / upstream API error |
| 8 | Preview not found, expired, or failed checks |
| 130 | Interrupted (Ctrl-C) |

## Safety model

Trade execution must pass **all** of these gates, in order:

1. `CAP_ALLOW_TRADING=true` — master switch (default off)
2. `CAP_DRY_RUN=false` — dry-run blocks everything
3. `--yes` on the command (when `CAP_REQUIRE_EXPLICIT_CONFIRM=true`)
4. A valid, unexpired preview whose risk checks all passed:
   - EPIC is in `CAP_ALLOWED_EPICS`
   - size within `CAP_MAX_POSITION_SIZE`, normalized to the broker's min/max/increment dealing rules
   - daily order counter under `CAP_MAX_ORDERS_PER_DAY`

There is no way to skip the preview step for positions and working orders — `execute-*` commands only accept a `preview_id`.

**Live trading:** keep `CAP_ENV=demo` until your workflow is proven. Switching to live requires editing `.env` (or passing `--live`) *and* having trading enabled — the defaults protect you twice.

## Architecture

```
capital_cli/
├── core/        # Capital.com services: config, HTTP client, session,
│                # rate limiter, risk engine, models, errors, WebSocket
└── cli/         # presentation: Typer apps per command group,
                 # Rich/JSON output, async runner with exit-code mapping
```

The `cli/` layer never talks to the API directly — every command parses arguments, calls a `core` service, and renders the result. All risk validation lives in `core/risk.py`, so safety rules cannot be bypassed by output or argument handling.

## Development

```bash
pip install -e ".[dev]"
pytest -q              # full test suite
ruff check .           # lint
mypy capital_cli       # type-check the whole package (matches CI)
```

An opt-in end-to-end suite runs against the real demo API (credentials required):

```bash
CAPCTL_E2E=1 pytest tests/e2e -m e2e -v
```

Tests mock the HTTP and WebSocket layers — no network or credentials needed.

Or use the task runner: `make check` (lint + typecheck + test), `make docs`, `make e2e`.

## Documentation

- [Full CLI reference](docs/CLI.md) — every command and option (auto-generated)
- [Scripting & automation](docs/scripting.md) — CI credentials, exit codes, jq recipes
- [Getting started from zero](docs/getting-started.md) — account, API key, install, first trade
- [Practical use cases](docs/use-cases.md) — what people actually do with capctl, with copy-pasteable scenarios
- [Troubleshooting](docs/troubleshooting.md) — common errors and exit codes
- [Contributing](CONTRIBUTING.md) — dev setup and conventions

## License

Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).

Licensed under the Apache License, Version 2.0. You may obtain a copy at
<http://www.apache.org/licenses/LICENSE-2.0>. Unless required by applicable law
or agreed to in writing, software distributed under the License is distributed
on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND.
