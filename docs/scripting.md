# Scripting & automation

capctl is built to be driven by scripts, cron, and CI. This page collects the
machine-facing contract in one place.

## Credentials in CI

Provide credentials via environment variables (never via flags — flags leak into
`ps` and shell history):

```bash
export CAP_API_KEY=...           # required
export CAP_IDENTIFIER=you@example.com
export CAP_API_PASSWORD=...       # the API-key custom password
export CAP_ENV=demo               # stay on demo until proven
```

Or point at a file with `--env-file /path/to/.env`.

## Non-interactive behavior

- capctl never prompts. Mutating commands require `--yes`; without it they **fail
  closed** (exit code 4) rather than hang — safe for CI.
- Use `--json` for machine-readable output and `--plain` for tab-delimited rows.
- Disable color with `--no-color` or `NO_COLOR=1`.
- The global flags `--json`, `--plain`, and `--no-color` work in **any
  position** — `capctl session status --json` is equivalent to
  `capctl --json session status`.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Unexpected internal error |
| 2 | Invalid input |
| 3 | Configuration error (missing/invalid credentials) |
| 4 | Safety policy block (trading disabled, dry-run, confirm required, epic not allowed, risk limit) |
| 5 | Authentication/session failure |
| 6 | Local rate limit exceeded |
| 7 | Broker / upstream API error |
| 8 | Preview not found, expired, or failed checks |
| 130 | Interrupted (Ctrl-C) |

Branch on them directly:

```bash
capctl --json trade execute-position "$PREVIEW" --yes
case $? in
  0) echo filled ;;
  4) echo "blocked by safety policy" ;;
  5) echo "auth problem" ;;
  7) echo "broker/upstream error" ;;
esac
```

## Safe retries & ambiguous confirmations

A confirmation result of `{"status": "TIMEOUT"}` (from `execute-position`,
`execute-order`, `close`, `cancel`, or `amend-*` with `--wait`) is **ambiguous**:
the request may have reached the broker and the order may have landed — capctl
simply stopped waiting for the confirmation. There is **no broker idempotency
key**, so blindly re-running `execute-*` can place a **duplicate** order.

On TIMEOUT, an automation or agent MUST reconcile before retrying:

```bash
capctl --json trade execute-position "$PREVIEW" --yes
# If the confirmation status is TIMEOUT, do NOT resend. Reconcile first:
capctl --json trade positions   # did the position appear?
capctl --json trade orders      # or did a working order land?
# Only retry execute-* if neither shows the intended order.
```

The same applies to `close`/`cancel`/`amend-*`: re-check `trade positions` /
`trade orders` to see whether the mutation already took effect.

## jq recipes

Extract the GOLD bid:

```bash
capctl --json market search --epics GOLD | jq -r '.markets[0].bid'
```

Export daily candles to CSV:

```bash
capctl --json market prices GOLD --resolution DAY --max 200 \
  | jq -r '.prices[] | [.snapshotTime, .openPrice.bid, .highPrice.bid, .lowPrice.bid, .closePrice.bid] | @csv'
```

<!-- NOTE: verify the .position.upl path against a real demo response before relying on this (tracked in the maintainer's manual e2e step). -->
Total unrealised P&L across open positions:

```bash
capctl --json trade positions | jq '[.positions[].position.upl] | add'
```

## Plain output without jq

```bash
capctl --plain market search --epics GOLD,SILVER | cut -f1,3
```
