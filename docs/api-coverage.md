# API coverage

How `capctl` commands map to the Capital.com Open API. "Covered" means a command
issues the request and surfaces the response (via tables or `--json`).

## General & session
| Endpoint | Command | Status |
|----------|---------|--------|
| `GET /time` | `session time` | Covered |
| `GET /ping` | `session ping` | Covered |
| `GET /session` | `session details` | Covered |
| `GET /session/encryptionKey` | `session encryption-key` | Covered (key fetch; encrypted-password login flow not used) |
| `POST /session` | `session login` | Covered |
| `PUT /session` | `session switch` | Covered |
| `DELETE /session` | `session logout` | Covered |

## Accounts
| Endpoint | Command | Status |
|----------|---------|--------|
| `GET /accounts` | `account list` | Covered |
| `GET /accounts/preferences` | `account prefs-get` | Covered |
| `PUT /accounts/preferences` | `account prefs-set` (`--hedging`, `--leverage`) | Covered |
| `GET /history/activity` | `account history-activity` | Covered |
| `GET /history/transactions` | `account history-transactions` | Covered |
| `POST /accounts/topUp` | `account topup` | Covered (demo only) |

## Markets
| Endpoint | Command | Status |
|----------|---------|--------|
| `GET /markets` | `market search` | Covered |
| `GET /markets/{epic}` | `market get` | Covered |
| `GET /marketnavigation` | `market nav-root` | Covered |
| `GET /marketnavigation/{id}` | `market nav-node` | Covered |
| `GET /prices/{epic}` | `market prices` | Covered |
| `GET /clientsentiment` | `market sentiment A,B` | Covered (batch) |
| `GET /clientsentiment/{id}` | `market sentiment A` | Covered |

## Trading
| Endpoint | Command | Status |
|----------|---------|--------|
| `GET /positions` | `trade positions` | Covered |
| `GET /positions/{dealId}` | `trade position` | Covered |
| `POST /positions` | `trade preview-position` → `trade execute-position` | Covered |
| `PUT /positions/{dealId}` | `trade amend-position` | Covered |
| `DELETE /positions/{dealId}` | `trade close` | Covered |
| `GET /workingorders` | `trade orders` | Covered |
| `POST /workingorders` | `trade preview-order` → `trade execute-order` | Covered |
| `PUT /workingorders/{dealId}` | `trade amend-order` | Covered |
| `DELETE /workingorders/{dealId}` | `trade cancel` | Covered |
| `GET /confirms/{dealReference}` | `trade confirm` | Covered |

## Watchlists
| Endpoint | Command | Status |
|----------|---------|--------|
| `GET /watchlists` | `watchlist list` | Covered |
| `POST /watchlists` | `watchlist create` | Covered |
| `GET /watchlists/{id}` | `watchlist get` | Covered |
| `PUT /watchlists/{id}` | `watchlist add` | Covered |
| `DELETE /watchlists/{id}` | `watchlist delete` | Covered |
| `DELETE /watchlists/{id}/{epic}` | `watchlist remove` | Covered |

## Streaming (WebSocket)
| Destination | Command | Status |
|-------------|---------|--------|
| `marketData.subscribe` (quotes) | `stream prices`, `stream alerts`, `stream portfolio` | Covered |
| `OHLCMarketData.subscribe` (candles) | `stream candles` | Covered |
| `ping` (keep-alive) | (internal) | Covered |

Not exposed as commands: the RSA encrypted-password login flow (the CLI uses the
standard credential login), and any endpoints Capital.com may add after this table
was written. Open an issue if something is missing.
