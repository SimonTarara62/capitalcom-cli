# Using capctl as a Python SDK (experimental)

> **EXPERIMENTAL.** The SDK is not yet 1.0. The documented import paths
> (`capital_cli.sdk.{CapitalComApp, CapitalComConfig, RiskPolicy}`) and the
> pydantic models in `capital_cli.core.models` are intended to be stable, but
> they **may shift between 0.x minors** until 1.0. Pin a version if you depend
> on them. See [Versioning](#versioning) below.

`capctl` is first and foremost a CLI, but the same tested broker engine — the
risk policy, the two-phase preview→execute flow, the rate limiter, the
WebSocket streaming — is available as an embeddable async Python SDK. Use the
CLI for the terminal, scripts, and CI; use the SDK to embed the engine in your
own Python (MCP servers, dashboards, n8n nodes, bots).

## Import paths

```python
from capital_cli.sdk import CapitalComApp, CapitalComConfig, RiskPolicy
```

- `CapitalComApp` — the async facade. Wire it up with `async with`, then reach
  the domain services through its attributes.
- `CapitalComConfig` — the public settings type; `CapitalComConfig.from_env()`
  reads credentials and safety settings from the environment / `.env` /
  `CAP_*_CMD` helpers exactly as the CLI does.
- `RiskPolicy` — a read-only snapshot of the risk limits in effect.

`CapitalComApp()` exposes these service attributes:

| Attribute | Service |
|-----------|---------|
| `app.markets` | market search, details, prices, sentiment, navigation |
| `app.accounts` | accounts, preferences, history, demo top-up |
| `app.watchlists` | list/get/create/add/remove/delete watchlists |
| `app.trading` | positions, orders, previews, guarded execution |
| `app.stream` | async iterators over the WebSocket stream |
| `app.session` | the session manager (login is handled for you) |
| `app.config` | the `CapitalComConfig` in effect |
| `app.risk_policy` | the `RiskPolicy` snapshot |

## Read-only example

`async with CapitalComApp() as app:` logs in (reusing a cached session when
available) and closes the shared HTTP client on exit. None of the methods below
have side effects.

```python
import asyncio

from capital_cli.sdk import CapitalComApp


async def main() -> None:
    async with CapitalComApp() as app:
        accounts = await app.accounts.list()
        print("active account:", accounts.get("active_account_id"))

        gold = await app.markets.get("GOLD")
        print("GOLD:", gold.get("snapshot", {}).get("bid"))

        positions = await app.trading.list_positions(limit=10)
        print("open positions:", len(positions.get("positions", [])))


asyncio.run(main())
```

Read methods return parsed JSON (`dict`) mirroring the Capital.com API
responses — the same payloads the CLI renders with `--json`.

## Preview → execute (places a real demo order)

Trade execution goes through the same two-phase flow and the same safety gates
as the CLI. You must first build a `PreviewPositionRequest`, preview it, check
that every risk check passed, and only then execute the returned `preview_id`.

> **This places a real order.** Even in the demo environment it hits the live
> broker. Trading also requires `CAP_ALLOW_TRADING=true`, the target EPIC in
> `CAP_ALLOWED_EPICS`, a size within your limits, and (by default)
> `confirm=True`. Keep `CAP_ENV=demo` until your workflow is proven.

```python
import asyncio

from capital_cli.core.models import Direction, PreviewPositionRequest
from capital_cli.sdk import CapitalComApp


async def main() -> None:
    async with CapitalComApp() as app:
        if not app.risk_policy.allow_trading:
            print("trading disabled — set CAP_ALLOW_TRADING=true to proceed")
            return

        req = PreviewPositionRequest(
            epic="GOLD",
            direction=Direction.BUY,
            size=0.5,
            stop_distance=15,
        )
        preview = await app.trading.preview_position(req)

        if not preview.all_checks_passed:
            for check in preview.checks:
                print(check.check, "->", "ok" if check.passed else check.message)
            return

        result = await app.trading.execute_position(
            preview.preview_id,
            confirm=True,
        )
        print("deal reference:", result.get("dealReference"))
        print("confirmation:", result.get("confirmation"))


asyncio.run(main())
```

Working orders follow the same shape with `PreviewWorkingOrderRequest` →
`app.trading.preview_working_order(...)` → `app.trading.execute_working_order(preview_id, confirm=True)`.

A `{"status": "TIMEOUT"}` confirmation is **ambiguous** — the order may have
landed. There is no broker idempotency key, so never blindly re-run
`execute_position` on a TIMEOUT; reconcile via `app.trading.list_positions()` /
`app.trading.list_orders()` first.

## Streaming

`app.stream.prices(...)` is an async generator that yields typed `PriceTick`
models until `duration` seconds elapse, then closes the WebSocket. Streaming
requires `CAP_WS_ENABLED=true`.

```python
import asyncio

from capital_cli.sdk import CapitalComApp


async def main() -> None:
    async with CapitalComApp() as app:
        async for tick in app.stream.prices(["BTCUSD"], duration=10):
            print(tick.epic, tick.bid, tick.offer)


asyncio.run(main())
```

Other stream iterators: `app.stream.candles(epics, resolutions, ...)` (yields
`OHLCBar`), `app.stream.alerts(epic, level, direction=..., ...)` (yields
`StreamAlert`), and `app.stream.portfolio(epics, ...)` (yields `PriceTick`).

## Risk policy

`app.risk_policy` is a frozen snapshot of the limits the engine is enforcing —
useful for guarding your own code before you attempt a trade:

```python
policy = app.risk_policy

policy.allow_trading             # bool — master switch (CAP_ALLOW_TRADING)
policy.allowed_epics             # list[str] — EPIC allowlist (CAP_ALLOWED_EPICS)
policy.max_position_size         # float — per-trade size ceiling
policy.max_working_order_size    # float — per-order size ceiling
policy.max_open_positions        # int — open-position cap
policy.max_orders_per_day        # int — daily order counter ceiling
policy.require_explicit_confirm  # bool — mutations need confirm=True
policy.dry_run                   # bool — blocks all executions when true
```

The snapshot is read-only; it reflects the config, not live counters. The
authoritative checks still run inside the engine on every preview/execute, so a
trade can be blocked even if your pre-check passed (e.g. the daily counter or
open-position limit is reached).

## Structured models

Consumers can rely on the pydantic models in `capital_cli.core.models`. The most
relevant ones:

- `PreviewPositionRequest`, `PreviewWorkingOrderRequest` — inputs to the preview
  methods.
- `PreviewResult` — returned by the preview methods (`preview_id`, `checks`,
  `all_checks_passed`, `estimated_entry`, `normalized_request`, `is_expired()`).
- `RiskCheck` — a single named check (`check`, `passed`, `message`).
- `Direction`, `WorkingOrderType`, `PriceResolution` — enums for request fields.
- `PriceTick`, `OHLCBar`, `StreamAlert` — yielded by the streaming iterators.

The read methods (`app.markets.*`, `app.accounts.*`, `app.watchlists.*`,
`app.trading.list_*`) return parsed JSON `dict`s rather than models, matching the
raw API responses.

## Limitations

- **One `CapitalComApp` per process.** The underlying services use
  process-global singletons (config, HTTP client, session manager, risk engine,
  rate limiter, state store), so constructing a second `CapitalComApp` with a
  different config in the same process is not supported yet.
- **A custom `CapitalComConfig` is installed process-wide.** Passing
  `CapitalComApp(config=...)` makes that config the global the services and risk
  engine read, and rebuilds the dependent singletons against it. It is not
  scoped to that one instance.
- `__aexit__` closes the shared HTTP client but deliberately does **not** log
  out, so the cached session can be reused across back-to-back runs.

## Versioning

Until 1.0 the SDK is **experimental**: import paths
(`capital_cli.sdk.{CapitalComApp, CapitalComConfig, RiskPolicy}`) and the
pydantic models are documented and intended-stable, but may shift between
0.x minors. From 1.0:
- Breaking changes to the SDK/service layer only in **major** versions.
- CLI UX may evolve in minors independently of the SDK contract.
- The `capital_cli.core.*` internals remain private (no compatibility promise);
  depend on `capital_cli.sdk` and `capital_cli.services` instead.
