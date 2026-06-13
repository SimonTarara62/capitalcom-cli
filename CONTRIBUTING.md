# Contributing

Thanks for considering a contribution!

New here? See [good first issues](docs/good-first-issues.md) for small, well-scoped
starter tasks, or browse issues labelled `good first issue` on GitHub.

## Development setup

```bash
git clone https://github.com/SimonTarara62/capitalcom-cli.git
cd capitalcom-cli
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Checks to run before a PR

```bash
pytest -q              # unit tests (offline, no credentials needed)
ruff check .           # lint
mypy capital_cli/cli   # type-check the CLI layer
```

There is also an opt-in end-to-end suite that hits the real demo API and
needs credentials in `.env`:

```bash
CAPCTL_E2E=1 pytest tests/e2e -m e2e -v
```

It opens and closes a minimum-size BTCUSD position on the **demo** account.

## Project layout

- `capital_cli/core/` — API client, session, risk engine, models, streaming.
  All safety rules live here.
- `capital_cli/cli/` — Typer commands. Thin: parse → call core → render.
- `tests/` — offline unit tests (mocked HTTP/WS); `tests/e2e/` — opt-in live suite.

## Conventions

- Commands always go through `run()` in `cli/runner.py` (exit-code mapping).
- Human output via `Output.record`/`Output.rows`; raw payloads via `Output.raw`.
  `--json` behavior is handled by `Output`, never inside commands.
- Anything that changes state takes `--yes`.
- Keep PRs focused; add tests for behavior you add or change.
