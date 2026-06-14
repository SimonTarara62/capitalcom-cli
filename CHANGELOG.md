# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Broker request no longer drops stop/profit fields that equal `0.0` (#8).
- E2E trade lifecycle skips gracefully when the market is not tradeable (#9).

### Added
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
