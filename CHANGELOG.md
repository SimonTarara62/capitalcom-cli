# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.6.1] - 2026-06-15

### Changed
- Made the project's **unofficial** status explicit in the README title/tagline,
  the package description (PyPI summary), the GitHub repository "About", and the
  `capctl --help` text. Added `docs/awesome-submission.md` tracking curated-list
  targets and their requirements. No API or behavior changes.

## [0.6.0] - 2026-06-14

### Added
- SDK parity: `app.session.server_time()`, `app.session.details()`, and
  `app.session.encryption_key()` — the SDK now covers the full Open API surface
  (coverage matrix 164/164, no N/A). The CLI `session time`/`details`/
  `encryption-key` commands share these methods.

### Changed
- The SDK is now positioned as **stable within 0.x** (no breaking changes without
  a deprecation cycle); dropped the "experimental" label across the README,
  `docs/sdk.md`, and module docstrings.
- README and `docs/api-coverage.md` now describe **full** (not "main") Open API
  coverage, backed by the automated matrix; the coverage badge is relabeled
  **CLI + SDK coverage**.

## [0.5.1] - 2026-06-14

### Added
- Verified full Capital.com Open API coverage: a canonical endpoint registry
  (`tests/e2e/endpoints.py`) plus CLI and SDK positive/negative e2e tests for
  every endpoint, a generated coverage matrix in `docs/api-coverage.md`, and a
  README **API coverage** badge backed by `docs/coverage-badge.json`.

### Fixed
- `trade execute-order`: working-order previews now persist the `type`/`level`
  fields to the state file, so executing a previewed working order from a
  separate CLI invocation no longer crashes with an internal `'type'` error.

## [0.5.0] - 2026-06-14

### Fixed
- Broker request no longer drops stop/profit fields that equal `0.0` (#8).
- E2E trade lifecycle skips gracefully when the market is not tradeable (#9).

### Added
- **Experimental SDK / service layer.** Broker logic now lives in a
  presentation-free `capital_cli.services` layer (markets, accounts, watchlists,
  trading, streaming) with a public facade `capital_cli.sdk`
  (`CapitalComApp`, `CapitalComConfig`, `RiskPolicy`) so other tools (MCP
  servers, dashboards, automation) can import the tested broker engine directly
  instead of shelling out to the CLI. Import paths/models are intended-stable but
  experimental until 1.0 — see [docs/sdk.md](docs/sdk.md). CLI commands are now
  thin wrappers over these services; behavior is unchanged.
- Session tokens are cached (0600, env-scoped, ≤10 min) so back-to-back commands
  don't re-login and hit HTTP 429; opt out with `CAP_PERSIST_SESSION=false` (#10).
- `--limit/-n` on `trade positions` and `trade orders` (#2).
- Windows CI job (#7).

## [0.4.0] - 2026-06-13

### Added
- `AGENTS.md` (single source of truth for AI agents) and a `CLAUDE.md` import stub.
- Auto-generated `docs/CLI.md` command reference, gated in CI.
- `Makefile` task runner (`test`/`lint`/`fmt`/`typecheck`/`docs`/`e2e`/`check`).
- `--no-color` global flag; honors `NO_COLOR` / `CAPCTL_NO_COLOR` / `TERM=dumb`.
- `--plain` tab-delimited output mode for piping.
- Loud LIVE-account banner before mutating trade commands.
- Shell-completion docs, `docs/scripting.md`, and a PyPI trusted-publishing job.

### Changed
- Package version is now single-sourced from `capital_cli.__version__`.
- Clearer remediation hints on confirm-required, dry-run, and epic-not-allowed errors.

## [0.3.0] - 2026-06-13

### Changed (safety — behavior change)
- Trade preview no longer silently adjusts the requested size. A size below the
  broker minimum or above the broker maximum now **fails** the preview instead of
  being clamped to the boundary, and a size that isn't a multiple of the broker
  increment fails unless you pass the new `trade preview-position`/`preview-order`
  flag `--auto-normalize-size`. Execution always uses the exact requested size (or
  the explicitly opted-in rounded size).
- `account prefs-set` is now gated by a mutation guard (dry-run + explicit confirm)
  instead of the trade-execution guard, so changing leverage/hedging no longer
  requires `CAP_ALLOW_TRADING=true`.

### Added
- `--auto-normalize-size` opt-in flag on `trade preview-position` and `preview-order`.

### Changed
- HTTP client now sends a descriptive `User-Agent` and, on an auth-expiry (401/403)
  during a safe GET, re-logs in and retries once before failing.
- CI type-checks the whole `capital_cli` package.
- Docs: added an API coverage table, clarified the CLI-vs-SDK scope and short-lived
  session model, aligned install instructions, and expanded the security guidance.

## [0.2.0] - 2026-06-13

### Added
- `stream candles` — live OHLC candlestick streaming over WebSocket
  (`OHLCMarketData.subscribe`), with selectable resolution and classic or
  heikin-ashi bars.
- `account prefs-set --leverage ASSET=VALUE` — configure per-asset-class leverage.

### Changed
- WebSocket keep-alive now uses the documented application-level `ping` message,
  keeping streaming sessions alive for their full lifetime.

## [0.1.0] - 2026-06-13

### Added
- Initial release of `capctl`, a command-line client for the Capital.com Open API.
- Command groups: `session`, `market`, `account`, `trade`, `watchlist`, `stream`,
  covering the full Capital.com Open API surface — including server time, session
  details and encryption key, single and batch client sentiment, market
  navigation, OHLC prices, account preferences and history, position/order
  preview, execution, amendment, closing, and cancellation.
- Two-phase guarded trading (preview → execute) with an allowlist, size and
  daily-order limits, dry-run, and explicit confirmation.
- Human-readable Rich tables with a global `--json` mode for scripting, and
  distinct process exit codes per failure class.
- Real-time WebSocket streaming for prices, alerts, and portfolio snapshots.
- Persistent state for trade previews and the daily order counter.
- Documentation: getting-started, use cases, troubleshooting, contributing.

[Unreleased]: https://github.com/SimonTarara62/capitalcom-cli/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/SimonTarara62/capitalcom-cli/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/SimonTarara62/capitalcom-cli/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/SimonTarara62/capitalcom-cli/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/SimonTarara62/capitalcom-cli/releases/tag/v0.1.0
