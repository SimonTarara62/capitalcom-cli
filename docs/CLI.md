# `capctl`

capctl — command-line client for the Capital.com Open API.

**Usage**:

```console
$ capctl [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--json`: Emit raw JSON instead of tables.
* `--env-file PATH`: Path to a .env credentials file.
* `--demo`: Force the demo environment.
* `--live`: Force the live environment.
* `-a, --account TEXT`: Account ID to use for this invocation.
* `-v, --verbose`: Enable debug logging.
* `--no-color`: Disable colored output (also honors NO_COLOR).
* `--plain`: Tab-delimited rows for piping (no boxes/colors).
* `--version`: Show version and exit.
* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `session`: Session lifecycle: login, ping, logout.
* `market`: Market data: search, prices, sentiment.
* `account`: Accounts: list, preferences, history.
* `trade`: Trading: positions, orders, preview, execute.
* `watchlist`: Watchlists: list, create, add, remove.
* `stream`: Real-time streaming: prices, alerts,...

## `capctl session`

Session lifecycle: login, ping, logout.

**Usage**:

```console
$ capctl session [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `status`: Show current session status (no network...
* `login`: Create (or verify) a session and store...
* `ping`: Keep the session alive.
* `logout`: End the session and clear tokens.
* `switch`: Switch the active account.
* `time`: Show the broker&#x27;s current server time (no...
* `details`: Show server-side session details (client...
* `encryption-key`: Fetch the API encryption key and timestamp...

### `capctl session status`

Show current session status (no network call).

**Usage**:

```console
$ capctl session status [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

### `capctl session login`

Create (or verify) a session and store auth tokens.

**Usage**:

```console
$ capctl session login [OPTIONS]
```

**Options**:

* `--force`: Re-login even if a session is valid.
* `-a, --account TEXT`: Account ID to switch to after login.
* `--help`: Show this message and exit.

### `capctl session ping`

Keep the session alive.

**Usage**:

```console
$ capctl session ping [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

### `capctl session logout`

End the session and clear tokens.

**Usage**:

```console
$ capctl session logout [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

### `capctl session switch`

Switch the active account.

**Usage**:

```console
$ capctl session switch [OPTIONS] ACCOUNT_ID
```

**Arguments**:

* `ACCOUNT_ID`: Target account ID.  [required]

**Options**:

* `--help`: Show this message and exit.

### `capctl session time`

Show the broker&#x27;s current server time (no authentication required).

**Usage**:

```console
$ capctl session time [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

### `capctl session details`

Show server-side session details (client id, account id, currency, timezone).

**Usage**:

```console
$ capctl session details [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

### `capctl session encryption-key`

Fetch the API encryption key and timestamp (used for encrypted-password login).

**Usage**:

```console
$ capctl session encryption-key [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `capctl market`

Market data: search, prices, sentiment.

**Usage**:

```console
$ capctl market [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `search`: Search markets by term or EPICs.
* `get`: Get full market details and dealing rules.
* `nav-root`: Get the root market-navigation tree.
* `nav-node`: Get child nodes/markets under a navigation...
* `prices`: Get historical OHLC prices.
* `sentiment`: Get client sentiment (long vs short %) for...

### `capctl market search`

Search markets by term or EPICs.

**Usage**:

```console
$ capctl market search [OPTIONS] [TERM]
```

**Arguments**:

* `[TERM]`: Search term, e.g. &#x27;Bitcoin&#x27;.

**Options**:

* `--epics TEXT`: Comma-separated EPICs to filter.
* `--limit INTEGER`: Max results.  [default: 50]
* `--help`: Show this message and exit.

### `capctl market get`

Get full market details and dealing rules.

**Usage**:

```console
$ capctl market get [OPTIONS] EPIC
```

**Arguments**:

* `EPIC`: Market EPIC.  [required]

**Options**:

* `--help`: Show this message and exit.

### `capctl market nav-root`

Get the root market-navigation tree.

**Usage**:

```console
$ capctl market nav-root [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

### `capctl market nav-node`

Get child nodes/markets under a navigation node.

**Usage**:

```console
$ capctl market nav-node [OPTIONS] NODE_ID
```

**Arguments**:

* `NODE_ID`: Navigation node ID.  [required]

**Options**:

* `--limit INTEGER`: Max child nodes/markets (&lt;=500).
* `--help`: Show this message and exit.

### `capctl market prices`

Get historical OHLC prices.

**Usage**:

```console
$ capctl market prices [OPTIONS] EPIC
```

**Arguments**:

* `EPIC`: Market EPIC.  [required]

**Options**:

* `--resolution TEXT`: MINUTE, MINUTE_5, MINUTE_15, MINUTE_30, HOUR, HOUR_4, DAY, WEEK.  [default: MINUTE_15]
* `--max INTEGER`: Max candles (&lt;=1000).  [default: 200]
* `--from TEXT`: Start date ISO 8601.
* `--to TEXT`: End date ISO 8601.
* `--help`: Show this message and exit.

### `capctl market sentiment`

Get client sentiment (long vs short %) for one or several markets.

**Usage**:

```console
$ capctl market sentiment [OPTIONS] MARKET_IDS
```

**Arguments**:

* `MARKET_IDS`: Market ID, or comma-separated IDs for a batch (e.g. &#x27;GOLD,SILVER&#x27;).  [required]

**Options**:

* `--help`: Show this message and exit.

## `capctl account`

Accounts: list, preferences, history.

**Usage**:

```console
$ capctl account [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `list`: List all trading accounts.
* `prefs-get`: Get account preferences (hedging, leverage).
* `prefs-set`: Set account preferences: hedging mode...
* `history-activity`: Get account activity history.
* `history-transactions`: Get transaction history.
* `topup`: Top up the demo account balance (demo...

### `capctl account list`

List all trading accounts.

**Usage**:

```console
$ capctl account list [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

### `capctl account prefs-get`

Get account preferences (hedging, leverage).

**Usage**:

```console
$ capctl account prefs-get [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

### `capctl account prefs-set`

Set account preferences: hedging mode and/or per-asset-class leverage (risk-gated).

**Usage**:

```console
$ capctl account prefs-set [OPTIONS]
```

**Options**:

* `--hedging / --no-hedging`: Enable/disable hedging mode.
* `--leverage TEXT`: Per asset class, e.g. --leverage CRYPTOCURRENCIES=2 (repeatable). Asset classes: SHARES, CURRENCIES, INDICES, CRYPTOCURRENCIES, COMMODITIES.
* `-y, --yes`: Confirm this risk-gated change.
* `--help`: Show this message and exit.

### `capctl account history-activity`

Get account activity history.

**Usage**:

```console
$ capctl account history-activity [OPTIONS]
```

**Options**:

* `--last INTEGER`: Last N seconds (max 86400).  [default: 600]
* `--from TEXT`: Start ISO 8601.
* `--to TEXT`: End ISO 8601.
* `--detailed`: Include full activity details.
* `--deal-id TEXT`: Filter to a single deal ID.
* `--help`: Show this message and exit.

### `capctl account history-transactions`

Get transaction history.

**Usage**:

```console
$ capctl account history-transactions [OPTIONS]
```

**Options**:

* `--last INTEGER`: Last N seconds.  [default: 600]
* `--type TEXT`: Transaction type filter.
* `--from TEXT`: Start ISO 8601.
* `--to TEXT`: End ISO 8601.
* `--help`: Show this message and exit.

### `capctl account topup`

Top up the demo account balance (demo environment only).

**Usage**:

```console
$ capctl account topup [OPTIONS] AMOUNT
```

**Arguments**:

* `AMOUNT`: Amount to add to the demo balance.  [required]

**Options**:

* `-y, --yes`: Confirm the top-up.
* `--help`: Show this message and exit.

## `capctl trade`

Trading: positions, orders, preview, execute.

**Usage**:

```console
$ capctl trade [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `positions`: List open positions.
* `position`: Get a single position by deal ID.
* `orders`: List working orders.
* `confirm`: Get (or wait for) a deal confirmation.
* `preview-position`: Validate a position against risk policy...
* `preview-order`: Validate a working order and return a...
* `execute-position`: Execute a previewed position (SIDE EFFECT).
* `execute-order`: Execute a previewed working order (SIDE...
* `close`: Close an open position (SIDE EFFECT).
* `cancel`: Cancel a working order (SIDE EFFECT).
* `amend-position`: Amend the stop-loss / take-profit on an...
* `amend-order`: Amend a working order&#x27;s level, expiry, or...

### `capctl trade positions`

List open positions.

**Usage**:

```console
$ capctl trade positions [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

### `capctl trade position`

Get a single position by deal ID.

**Usage**:

```console
$ capctl trade position [OPTIONS] DEAL_ID
```

**Arguments**:

* `DEAL_ID`: Position deal ID.  [required]

**Options**:

* `--help`: Show this message and exit.

### `capctl trade orders`

List working orders.

**Usage**:

```console
$ capctl trade orders [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

### `capctl trade confirm`

Get (or wait for) a deal confirmation.

**Usage**:

```console
$ capctl trade confirm [OPTIONS] DEAL_REFERENCE
```

**Arguments**:

* `DEAL_REFERENCE`: Deal reference (e.g. o_...).  [required]

**Options**:

* `--wait`: Poll until ACCEPTED/REJECTED.
* `--timeout FLOAT`: Polling timeout in seconds.  [default: 15.0]
* `--help`: Show this message and exit.

### `capctl trade preview-position`

Validate a position against risk policy and return a preview_id (no trade).

**Usage**:

```console
$ capctl trade preview-position [OPTIONS] EPIC DIRECTION SIZE
```

**Arguments**:

* `EPIC`: Market EPIC.  [required]
* `DIRECTION`: BUY or SELL.  [required]
* `SIZE`: Position size.  [required]

**Options**:

* `--stop-level FLOAT`
* `--stop-distance FLOAT`
* `--profit-level FLOAT`
* `--profit-distance FLOAT`
* `--guaranteed-stop`
* `--trailing-stop`
* `--auto-normalize-size`: Round size to the broker increment instead of failing.
* `--help`: Show this message and exit.

### `capctl trade preview-order`

Validate a working order and return a preview_id (no order created).

**Usage**:

```console
$ capctl trade preview-order [OPTIONS] EPIC DIRECTION ORDER_TYPE LEVEL SIZE
```

**Arguments**:

* `EPIC`: Market EPIC.  [required]
* `DIRECTION`: BUY or SELL.  [required]
* `ORDER_TYPE`: LIMIT or STOP.  [required]
* `LEVEL`: Trigger level.  [required]
* `SIZE`: Order size.  [required]

**Options**:

* `--stop-level FLOAT`
* `--profit-level FLOAT`
* `--good-till TEXT`: Expiry ISO 8601.
* `--auto-normalize-size`: Round size to the broker increment instead of failing.
* `--help`: Show this message and exit.

### `capctl trade execute-position`

Execute a previewed position (SIDE EFFECT).

**Usage**:

```console
$ capctl trade execute-position [OPTIONS] PREVIEW_ID
```

**Arguments**:

* `PREVIEW_ID`: Preview ID from preview-position.  [required]

**Options**:

* `-y, --yes`: Confirm execution (creates a real trade).
* `--wait / --no-wait`: Wait for broker confirmation.  [default: wait]
* `--timeout FLOAT`: [default: 15.0]
* `--help`: Show this message and exit.

### `capctl trade execute-order`

Execute a previewed working order (SIDE EFFECT).

**Usage**:

```console
$ capctl trade execute-order [OPTIONS] PREVIEW_ID
```

**Arguments**:

* `PREVIEW_ID`: Preview ID from preview-order.  [required]

**Options**:

* `-y, --yes`: Confirm execution (creates a real order).
* `--wait / --no-wait`: Wait for broker confirmation.  [default: wait]
* `--timeout FLOAT`: [default: 15.0]
* `--help`: Show this message and exit.

### `capctl trade close`

Close an open position (SIDE EFFECT).

**Usage**:

```console
$ capctl trade close [OPTIONS] DEAL_ID
```

**Arguments**:

* `DEAL_ID`: Position deal ID to close.  [required]

**Options**:

* `-y, --yes`: Confirm closing the position.
* `--wait / --no-wait`: Wait for broker confirmation.  [default: wait]
* `--timeout FLOAT`: [default: 15.0]
* `--help`: Show this message and exit.

### `capctl trade cancel`

Cancel a working order (SIDE EFFECT).

**Usage**:

```console
$ capctl trade cancel [OPTIONS] DEAL_ID
```

**Arguments**:

* `DEAL_ID`: Working order deal ID to cancel.  [required]

**Options**:

* `-y, --yes`: Confirm cancelling the order.
* `--wait / --no-wait`: Wait for broker confirmation.  [default: wait]
* `--timeout FLOAT`: [default: 15.0]
* `--help`: Show this message and exit.

### `capctl trade amend-position`

Amend the stop-loss / take-profit on an open position (SIDE EFFECT).

**Usage**:

```console
$ capctl trade amend-position [OPTIONS] DEAL_ID
```

**Arguments**:

* `DEAL_ID`: Deal ID of the open position to amend.  [required]

**Options**:

* `--stop-level FLOAT`
* `--stop-distance FLOAT`
* `--profit-level FLOAT`
* `--profit-distance FLOAT`
* `--guaranteed-stop / --no-guaranteed-stop`: Toggle guaranteed stop.
* `--trailing-stop / --no-trailing-stop`: Toggle trailing stop.
* `-y, --yes`: Confirm the amendment.
* `--wait / --no-wait`: Wait for broker confirmation.  [default: wait]
* `--timeout FLOAT`: [default: 15.0]
* `--help`: Show this message and exit.

### `capctl trade amend-order`

Amend a working order&#x27;s level, expiry, or stops/limits (SIDE EFFECT).

**Usage**:

```console
$ capctl trade amend-order [OPTIONS] DEAL_ID
```

**Arguments**:

* `DEAL_ID`: Deal ID of the working order to amend.  [required]

**Options**:

* `--level FLOAT`: New trigger level.
* `--good-till TEXT`: New expiry ISO 8601.
* `--stop-level FLOAT`
* `--stop-distance FLOAT`
* `--profit-level FLOAT`
* `--profit-distance FLOAT`
* `-y, --yes`: Confirm the amendment.
* `--wait / --no-wait`: Wait for broker confirmation.  [default: wait]
* `--timeout FLOAT`: [default: 15.0]
* `--help`: Show this message and exit.

## `capctl watchlist`

Watchlists: list, create, add, remove.

**Usage**:

```console
$ capctl watchlist [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `list`: List all watchlists.
* `get`: Get a watchlist and its markets.
* `create`: Create a new watchlist.
* `add`: Add a market to a watchlist.
* `remove`: Remove a market from a watchlist.
* `delete`: Delete a watchlist.

### `capctl watchlist list`

List all watchlists.

**Usage**:

```console
$ capctl watchlist list [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

### `capctl watchlist get`

Get a watchlist and its markets.

**Usage**:

```console
$ capctl watchlist get [OPTIONS] WATCHLIST_ID
```

**Arguments**:

* `WATCHLIST_ID`: Watchlist ID.  [required]

**Options**:

* `--help`: Show this message and exit.

### `capctl watchlist create`

Create a new watchlist.

**Usage**:

```console
$ capctl watchlist create [OPTIONS] NAME
```

**Arguments**:

* `NAME`: Watchlist name.  [required]

**Options**:

* `-y, --yes`: Confirm creation.
* `--help`: Show this message and exit.

### `capctl watchlist add`

Add a market to a watchlist.

**Usage**:

```console
$ capctl watchlist add [OPTIONS] WATCHLIST_ID EPIC
```

**Arguments**:

* `WATCHLIST_ID`: Watchlist ID.  [required]
* `EPIC`: Market EPIC to add.  [required]

**Options**:

* `-y, --yes`: Confirm.
* `--help`: Show this message and exit.

### `capctl watchlist remove`

Remove a market from a watchlist.

**Usage**:

```console
$ capctl watchlist remove [OPTIONS] WATCHLIST_ID EPIC
```

**Arguments**:

* `WATCHLIST_ID`: Watchlist ID.  [required]
* `EPIC`: Market EPIC to remove.  [required]

**Options**:

* `-y, --yes`: Confirm.
* `--help`: Show this message and exit.

### `capctl watchlist delete`

Delete a watchlist.

**Usage**:

```console
$ capctl watchlist delete [OPTIONS] WATCHLIST_ID
```

**Arguments**:

* `WATCHLIST_ID`: Watchlist ID.  [required]

**Options**:

* `-y, --yes`: Confirm deletion.
* `--help`: Show this message and exit.

## `capctl stream`

Real-time streaming: prices, alerts, portfolio.

**Usage**:

```console
$ capctl stream [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `prices`: Stream live bid/offer prices.
* `alerts`: Trigger an alert when a market crosses a...
* `portfolio`: Stream live price snapshots for currently...
* `candles`: Stream live OHLC candlesticks.

### `capctl stream prices`

Stream live bid/offer prices.

**Usage**:

```console
$ capctl stream prices [OPTIONS] EPICS
```

**Arguments**:

* `EPICS`: Comma-separated EPICs (max 40).  [required]

**Options**:

* `--duration FLOAT`: Stream duration in seconds.  [default: 300.0]
* `--interval FLOAT`: Min seconds between recorded updates.  [default: 1.0]
* `--help`: Show this message and exit.

### `capctl stream alerts`

Trigger an alert when a market crosses a price level.

**Usage**:

```console
$ capctl stream alerts [OPTIONS] EPIC LEVEL
```

**Arguments**:

* `EPIC`: Market EPIC to watch.  [required]
* `LEVEL`: Trigger price level.  [required]

**Options**:

* `--direction TEXT`: ABOVE or BELOW.  [default: ABOVE]
* `--duration FLOAT`: Max monitoring seconds.  [default: 300.0]
* `--auto-close / --keep-open`: Stop after first trigger.  [default: auto-close]
* `--help`: Show this message and exit.

### `capctl stream portfolio`

Stream live price snapshots for currently open positions.

**Usage**:

```console
$ capctl stream portfolio [OPTIONS]
```

**Options**:

* `--duration FLOAT`: Stream duration in seconds.  [default: 300.0]
* `--interval FLOAT`: Recording interval in seconds.  [default: 5.0]
* `--help`: Show this message and exit.

### `capctl stream candles`

Stream live OHLC candlesticks.

**Usage**:

```console
$ capctl stream candles [OPTIONS] EPICS
```

**Arguments**:

* `EPICS`: Comma-separated EPICs (max 40).  [required]

**Options**:

* `--resolution TEXT`: MINUTE, MINUTE_5, MINUTE_15, MINUTE_30, HOUR, HOUR_4, DAY, WEEK.  [default: MINUTE]
* `--type TEXT`: classic or heikin-ashi.  [default: classic]
* `--duration FLOAT`: Stream duration in seconds.  [default: 300.0]
* `--interval FLOAT`: Min seconds between recorded bars (0 = every update).  [default: 0.0]
* `--help`: Show this message and exit.
