# Practical use cases

Worked scenarios showing what `capctl` is actually for. Every command here is
copy-pasteable; anything that trades assumes the **demo** environment (the
default) with trading enabled in `.env` for the markets involved.

If you're brand new, do the [getting-started guide](getting-started.md) first.

---

## 1. Practice trading without risking a cent

**Who:** anyone learning how leveraged trading works.
**Value:** the demo account uses virtual money, and capctl's guardrails mirror
the discipline you'd want with real money — so the habits you build are the
safe ones.

```bash
# Research the market
capctl market get GOLD                 # dealing rules, spread, current price
capctl market sentiment GOLD           # what % of traders are long vs short
capctl market prices GOLD --resolution DAY --max 30   # last 30 daily candles

# Plan the trade with a stop-loss, validate it (creates NOTHING):
capctl trade preview-position GOLD BUY 0.5 --stop-distance 15 --profit-distance 30
# → table of risk checks + a preview_id

# Execute the validated plan, then watch it:
capctl trade execute-position <preview_id> --yes
capctl trade positions

# Move your stop to lock in profit, or widen your target — without re-opening:
capctl trade amend-position <dealId> --stop-level <new_stop> --profit-level <new_target> --yes

# Close when done:
capctl trade close <dealId> --yes
```

The two-phase flow is the point: you always see the risk checks and the
normalized size *before* anything reaches the broker. When you eventually
study a real strategy, you can rehearse the entire routine here daily.

## 2. The 10-second morning check

**Who:** anyone with open positions.
**Value:** account state without opening a browser, logging in, and clicking.

```bash
capctl account list && capctl trade positions && capctl trade orders
```

Make it one word with a shell alias:

```bash
alias morning='capctl account list && capctl trade positions && capctl trade orders'
```

## 3. Price alerts while you work

**Who:** anyone waiting for a level to be hit.
**Value:** instead of staring at charts, let the terminal watch the market.

```bash
# Tell me when Bitcoin crosses 75,000 (watches up to 1 hour, exits on trigger):
capctl stream alerts BTCUSD 75000 --direction ABOVE --duration 3600
```

Because it's a normal command, you can chain anything onto the trigger —
a sound, a desktop notification, another capctl command:

```bash
capctl stream alerts BTCUSD 75000 --direction ABOVE --duration 3600 \
  && say "bitcoin breakout"        # macOS; use notify-send on Linux
```

## 4. Market data for analysis (CSV / spreadsheets / pandas)

**Who:** data-curious traders, students, quant hobbyists.
**Value:** historical OHLC candles as clean data, no manual exporting.

```bash
# 200 daily GOLD candles → CSV
capctl --json market prices GOLD --resolution DAY --max 200 \
  | jq -r '.prices[] | [.snapshotTime, .openPrice.bid, .highPrice.bid, .lowPrice.bid, .closePrice.bid] | @csv' \
  > gold_daily.csv
```

Then open it in Excel, or in Python:

```python
import pandas as pd
df = pd.read_csv("gold_daily.csv", names=["time", "open", "high", "low", "close"])
print(df["close"].pct_change().describe())
```

Prefer live candles over polling? Stream OHLC bars straight to a file:

```bash
capctl --json stream candles BTCUSD --resolution MINUTE_5 --duration 600 \
  | jq -c '.bars[]' >> btc_5m_live.jsonl
```

Resolutions go from `MINUTE` to `WEEK`, so the same one-liner covers intraday
research and long-term studies.

## 5. Hands-free monitoring with cron

**Who:** anyone who wants a record of their account over time.
**Value:** an append-only JSON log of positions/balance you can analyze later —
the platform won't give you that history in this form.

```bash
# crontab -e — snapshot positions every 15 minutes during the day:
*/15 8-22 * * 1-5  capctl --json trade positions >> ~/logs/positions.jsonl 2>&1

# Daily balance record at 18:00:
0 18 * * *  capctl --json account list >> ~/logs/balance.jsonl 2>&1
```

Each line is a timestampable JSON document — `jq`, a spreadsheet import, or a
pandas one-liner turns it into an equity curve.

## 6. Safe building block for your own automation

**Who:** developers scripting trading workflows.
**Value:** you script the *workflow*, capctl keeps the *guardrails* — your bash
bug cannot exceed position-size limits, trade outside the allowlist, or skip
the confirmation gate, because those rules live below the command line.

```bash
#!/usr/bin/env bash
# Example: enter a position only if the preview passes all risk checks.
set -euo pipefail

PREVIEW_JSON=$(capctl --json trade preview-position GOLD BUY 0.5 --stop-distance 15)
PASSED=$(echo "$PREVIEW_JSON" | jq -r '.all_checks_passed')

if [ "$PASSED" = "true" ]; then
  PREVIEW_ID=$(echo "$PREVIEW_JSON" | jq -r '.preview_id')
  capctl --json trade execute-position "$PREVIEW_ID" --yes
else
  echo "Risk checks failed:" >&2
  echo "$PREVIEW_JSON" | jq -r '.checks[] | select(.passed == false) | .message' >&2
  exit 1
fi
```

Exit codes are designed for this — branch on the failure *class*:

```bash
capctl --json trade execute-position "$PREVIEW_ID" --yes
case $? in
  0) echo "filled" ;;
  4) echo "blocked by safety policy — not an error, the guardrails worked" ;;
  5) echo "auth problem — check credentials" ;;
  7) echo "broker/upstream error — maybe retry later" ;;
esac
```

(Full table in the [README](../README.md#exit-codes).)

## 7. Interactive explorer for the Capital.com API

**Who:** developers building their own Capital.com integration in any language.
**Value:** `--json` output is the real API response — so instead of reading
docs and guessing, you poke the live (demo) API from your shell and see exactly
what comes back, with authentication, session keep-alive, and rate limiting
already handled.

```bash
capctl --json market get BTCUSD | jq '.dealingRules'   # what sizes are legal?
capctl --json trade positions | jq '.positions[0]'      # what does a position object look like?
capctl --json account history-activity --last 86400     # what lands in the activity feed?
```

When your own code misbehaves, comparing its requests against what capctl
sends is a fast way to find the difference.

## 8. Watchlists as code

**Who:** anyone tracking a basket of markets.
**Value:** reproducible watchlists — rebuild or sync them from a script instead
of clicking through the UI, and review them from the terminal.

```bash
capctl watchlist create "Metals" --yes
WL=$(capctl --json watchlist list | jq -r '.watchlists[] | select(.name=="Metals") | .id')
for epic in GOLD SILVER COPPER; do
  capctl watchlist add "$WL" "$epic" --yes
done
capctl watchlist get "$WL"
```

---

## What capctl is *not* for

Honesty section. It is not a trading bot (it executes what you tell it, when
you tell it), not a strategy backtester, not a charting tool, and not financial
advice. It is the reliable, guarded plumbing between you (or your scripts) and
the Capital.com API — what you build on top is up to you.

Next: [README command reference](../README.md#command-reference) ·
[troubleshooting](troubleshooting.md)
