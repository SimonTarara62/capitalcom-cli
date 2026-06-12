# Troubleshooting

## How to read failures

`capctl` prints errors to stderr as `Error (CODE): message` (or JSON with
`--json`) and exits with a code that tells you the failure *class*:

| Exit code | Class | Typical cause & fix |
|-----------|-------|---------------------|
| 1 | Internal/unexpected | Re-run with `--verbose`; if it persists, open an issue with the output |
| 2 | Invalid input | A flag or argument failed validation — check `--help` for the command |
| 3 | Configuration | `.env` missing or incomplete — see below |
| 4 | Safety policy | Trading disabled / confirmation missing / EPIC not allowed / risk limit |
| 5 | Authentication | Wrong credentials or expired session — see below |
| 6 | Local rate limit | You're sending commands too fast; wait a second |
| 7 | Broker / upstream | Capital.com rejected the request (market closed, insufficient funds, outage) |
| 8 | Preview problem | Preview id wrong, older than 2 minutes, or its checks failed |

## Common problems

### `capctl: command not found`
The virtualenv isn't active. Run `source .venv/bin/activate` (Windows:
`.venv\Scripts\activate`), or install globally with `pipx install .`.

### Exit 3: "Field required" mentioning `cap_api_key` / `cap_identifier` / `cap_api_password`
The CLI can't find your credentials. Confirm `.env` exists in the directory
you're running from (or pass `--env-file /path/to/.env`), and that all
three values are filled in.

### Exit 5: authentication failed
- `CAP_API_PASSWORD` must be the **custom password you set when generating
  the API key**, not your Capital.com account password.
- The API key may be expired or revoked — generate a new one in
  **Settings → API integrations**.
- Check you're on the right environment: a demo key won't work with
  `--live` and vice versa.

### Exit 4: "Trading is disabled"
Set `CAP_ALLOW_TRADING=true` in `.env` — and list the markets you want in
`CAP_ALLOWED_EPICS` (e.g. `GOLD,BTCUSD`, or `ALL`).

### Exit 4: "Explicit confirmation required"
Add `--yes` to the command. This is deliberate friction for anything that
changes state.

### Exit 4: "Epic 'X' not in allowlist"
Add the EPIC to `CAP_ALLOWED_EPICS` in `.env`.

### Exit 8: "Preview ... expired"
Previews are valid for 120 seconds. Run the preview command again and
execute the fresh `preview_id`.

### Exit 7 on execute: market closed / rejected
Stock and commodity markets have trading hours; try a 24/7 market like
`BTCUSD` to verify your setup, or retry during market hours. The
confirmation message from the broker (shown in the output) says why.

### HTTP 429: error.too-many.requests on login
Capital.com limits how often you can create sessions. Wait a couple of
minutes and try again. Scripts that fire many capctl commands in a tight
loop should pause ~1 second between them.

### `WebSocket streaming is disabled`
Set `CAP_WS_ENABLED=true` in `.env`. Streaming also requires valid login
credentials.

### Streaming shows no ticks
Quiet markets tick rarely outside their trading hours. Try `BTCUSD`, which
trades around the clock.

### Where is my state stored?
Trade previews and the daily order counter persist in
`~/.config/capital-cli/state.json` (override with `CAPCTL_STATE_FILE`) so
they survive between commands. Deleting the file is safe (you'll just lose
unexecuted previews).

## Still stuck?

Run the failing command with `--verbose` and open a GitHub issue including
the command, the output (it never contains your secrets), and your OS and
Python version.
