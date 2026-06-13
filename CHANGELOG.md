# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-06-13

### Added
- Initial release of `capctl`, a command-line client for the Capital.com Open API.
- Command groups: `session`, `market`, `account`, `trade`, `watchlist`, `stream`.
- Two-phase guarded trading (preview → execute) with an allowlist, size and
  daily-order limits, dry-run, and explicit confirmation.
- Human-readable Rich tables with a global `--json` mode for scripting, and
  distinct process exit codes per failure class.
- Real-time WebSocket streaming for prices, alerts, and portfolio snapshots.
- Persistent state for trade previews and the daily order counter.
- Documentation: getting-started, use cases, troubleshooting, contributing.

[Unreleased]: https://github.com/SimonTarara62/capitalcom-cli/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/SimonTarara62/capitalcom-cli/releases/tag/v0.1.0
