"""Run core coroutines and translate errors into process exit codes.

Centralizes three concerns in one place so commands stay thin:
  1. domain error -> distinct process exit code,
  2. pydantic ValidationError -> friendly field-by-field message (exit 2),
  3. DEBUG timing logs (duration in ms, failure type) for --verbose.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

import typer
from pydantic import ValidationError

from capital_cli.cli.output import Output
from capital_cli.core.errors import CapitalCLIError, ErrorCode

logger = logging.getLogger("capctl")

T = TypeVar("T")

# Distinct exit codes per error class so scripts can branch on failures.
# 2 = bad input (matches the conventional CLI "usage error" code).
EXIT_CODES: dict[str, int] = {
    ErrorCode.INVALID_REQUEST: 2,
    ErrorCode.CONFIG_MISSING: 3,
    ErrorCode.CONFIG_INVALID: 3,
    ErrorCode.TRADING_DISABLED: 4,
    ErrorCode.DRY_RUN_ENABLED: 4,
    ErrorCode.CONFIRM_REQUIRED: 4,
    ErrorCode.EPIC_NOT_ALLOWED: 4,
    ErrorCode.RISK_LIMIT: 4,
    ErrorCode.SESSION_EXPIRED: 5,
    ErrorCode.SESSION_NOT_INITIALIZED: 5,
    ErrorCode.AUTH_FAILED: 5,
    ErrorCode.RATE_LIMITED_LOCAL: 6,
    ErrorCode.BROKER_REJECTED: 7,
    ErrorCode.UPSTREAM_ERROR: 7,
    ErrorCode.UPSTREAM_TIMEOUT: 7,
    ErrorCode.PREVIEW_NOT_FOUND: 8,
    ErrorCode.PREVIEW_EXPIRED: 8,
    ErrorCode.PREVIEW_CHECKS_FAILED: 8,
}


def _format_validation_error(exc: ValidationError) -> str:
    """Turn a pydantic ValidationError into a one-line, field-by-field message."""
    parts = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", ())) or "input"
        parts.append(f"{loc}: {err.get('msg', 'invalid')}")
    return "Invalid input — " + "; ".join(parts)


def run(
    out: Output,
    factory: Callable[[], Coroutine[Any, Any, T]],
    *,
    label: str | None = None,
) -> T:
    """
    Execute an async factory, rendering any failure and raising typer.Exit.

    Returns the coroutine result on success. `label` (optional) names the
    command for DEBUG timing logs; omitting it keeps call sites terse.
    """
    started = time.monotonic()
    name = label or "command"

    def _elapsed_ms() -> float:
        return (time.monotonic() - started) * 1000

    try:
        result = asyncio.run(factory())
        logger.debug("%s completed in %.0f ms", name, _elapsed_ms())
        return result
    except ValidationError as exc:
        logger.debug("%s failed (ValidationError) in %.0f ms", name, _elapsed_ms())
        out.error(ErrorCode.INVALID_REQUEST, _format_validation_error(exc))
        raise typer.Exit(code=EXIT_CODES[ErrorCode.INVALID_REQUEST]) from exc
    except CapitalCLIError as exc:
        logger.debug("%s failed (%s) in %.0f ms", name, exc.code, _elapsed_ms())
        out.error(exc.code, exc.message)
        raise typer.Exit(code=EXIT_CODES.get(exc.code, 1)) from exc
    except KeyboardInterrupt:
        out.note("Interrupted.")
        raise typer.Exit(code=130) from None
    except Exception as exc:  # noqa: BLE001 - top-level CLI guard
        logger.debug("%s failed (%s) in %.0f ms", name, type(exc).__name__, _elapsed_ms())
        out.error(ErrorCode.INTERNAL_ERROR, str(exc))
        raise typer.Exit(code=1) from exc
