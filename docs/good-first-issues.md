# Good first issues

Small, self-contained tasks that are a good way to make a first contribution.
Each is scoped to roughly one command or one test file, follows an existing
pattern, and has clear acceptance criteria. Pick one, comment on the matching
GitHub issue to claim it, and open a PR.

## 1. Add `--limit` to `trade positions` / `trade orders`
Large accounts return many rows. Add an optional `--limit N` that truncates the
rendered table (and the JSON list) the way `market search --limit` already does.
*Touches:* `capital_cli/cli/trade_cmds.py`, `tests/test_trade_cmds.py`.

## 2. Add a `--watch` refresh mode to `trade positions`
Re-render the positions table every N seconds until Ctrl-C, reusing the Rich
`Live` pattern from `capital_cli/cli/stream_cmds.py`.
*Touches:* `capital_cli/cli/trade_cmds.py`.

## 3. Friendlier empty-state messages
When a list command has no rows (no positions, no watchlists), print a short hint
instead of an empty table — e.g. "No open positions." Confirm `--json` still emits
`[]`.
*Touches:* `capital_cli/cli/output.py` (already has a "No results." path — extend
callers to pass a context-specific message).

## 4. Document every exit code with a worked example
Expand `docs/troubleshooting.md` so each exit code (2–8) has a one-line example
command that produces it.
*Touches:* `docs/troubleshooting.md`.

## 5. Add a `just`/`make` task runner
Add a `Makefile` (or `justfile`) with `install`, `test`, `lint`, `typecheck`,
and `e2e` targets that wrap the documented commands.
*Touches:* new `Makefile`, `CONTRIBUTING.md`.

## 6. Windows CI job
Add a `windows-latest` entry to the CI matrix in `.github/workflows/ci.yml` and
fix anything that surfaces (path handling, completion).
*Touches:* `.github/workflows/ci.yml`.

If none of these fit, open a feature request describing what you'd like to work
on — see [CONTRIBUTING](../CONTRIBUTING.md).
