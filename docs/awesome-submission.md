# Awesome-list submission tracker

Where to get `capitalcom-cli` listed, what each list requires, and the exact
entry text to submit. Keep this in sync when a submission lands.

## Targets

### 1. wilsonfreitas/awesome-quant — section "Trading & Backtesting" (Python)
- **Bar:** quality-based — documented, tested, fills a gap. No star/age minimum.
- **Status:** eligible now.
- **Format:** `[name](link) - Python - Description.`
- **Entry to submit:**
  `[capitalcom-cli](https://github.com/SimonTarara62/capitalcom-cli) - Python - Unofficial CLI and async SDK for the Capital.com broker API: market data, guarded order execution, and real-time streaming.`
- **How:** fork, add the entry alphabetically/at the end of the "Trading & Backtesting"
  list, one entry, PR titled `Add capitalcom-cli`. Verify the live section name and
  format before submitting (lists drift).

### 2. agarrharr/awesome-cli-apps — section "Finance"
- **Bar:** repo **> 90 days old** AND **> 20 GitHub stars**; one entry per PR;
  PR titled `Add capctl`; entry appended to the Finance category;
  `[name](link) - Description.` (capital start, period end, concise, no "CLI").
- **Status:** NOT eligible yet. Repo created 2026-06-12 → eligible **≈ 2026-09-10**,
  and only once stars ≥ 20.
- **Entry to submit (when eligible):**
  `[capctl](https://github.com/SimonTarara62/capitalcom-cli) - Unofficial client for the Capital.com trading API with guarded order execution and real-time streaming.`

### 3. toolleeo/awesome-cli-apps-in-a-csv — optional, CSV-format, broad inclusion
- **Status:** eligible; lower priority. Follow that repo's CSV row format if pursued.

## Unofficial positioning (done in this change set)

Distribution channels (PyPI, Homebrew tap, Terminal Trove) are tracked in
[distribution.md](distribution.md).

"Unofficial" is now explicit in: the README title + tagline, the existing risk
disclaimer, the `NOTICE` file, the `pyproject.toml` description (→ PyPI summary),
the GitHub repo "About", and the `capctl --help` text.

## MCP-safety note
Listing/positioning changes are text-only. The package name (`capital_cli` /
`capitalcom-cli`), the CLI binary (`capctl`), and the SDK public API are unchanged,
so the sibling MCP server that imports `capital_cli.sdk` is unaffected.
