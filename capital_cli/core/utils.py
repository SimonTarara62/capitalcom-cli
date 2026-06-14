"""Utility functions for Capital.com CLI."""

import asyncio
from collections.abc import Callable
from typing import Any, TypeVar

import httpx

T = TypeVar("T")

# Transient/network errors are worth retrying while polling; everything else
# (broker rejections, upstream 4xx/5xx surfaced as CapitalCLIError, programming
# errors) must propagate so the caller doesn't mistake a rejection for a timeout.
_TRANSIENT_ERRORS = (httpx.TransportError, asyncio.TimeoutError)


async def poll_until(
    fn: Callable[[], Any],
    condition: Callable[[Any], bool],
    *,
    timeout_s: float = 15.0,
    poll_interval_ms: int = 500,
    initial_delay_ms: int = 200,
) -> Any | None:
    """
    Poll a function until a condition is met or timeout.

    Only transient/network errors (httpx.TransportError, asyncio.TimeoutError)
    are swallowed and retried. Any other exception — notably CapitalCLIError /
    UpstreamError / BrokerError raised for a broker rejection — propagates so the
    caller can report the real failure instead of masking it as a timeout.

    Args:
        fn: Async function to call
        condition: Condition function that checks the result
        timeout_s: Timeout in seconds
        poll_interval_ms: Poll interval in milliseconds
        initial_delay_ms: Initial delay before first poll

    Returns:
        Result if condition met, None if timeout.
    """
    import time

    start_time = time.monotonic()

    # Initial delay
    if initial_delay_ms > 0:
        await asyncio.sleep(initial_delay_ms / 1000.0)

    while True:
        elapsed = time.monotonic() - start_time
        if elapsed >= timeout_s:
            return None

        try:
            result = await fn()
            if condition(result):
                return result
        except _TRANSIENT_ERRORS:
            # Continue polling on transient/network errors only.
            pass

        # Wait before next attempt
        await asyncio.sleep(poll_interval_ms / 1000.0)


def format_iso_datetime(dt: Any | None) -> str | None:
    """Format datetime to ISO 8601 string."""
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    try:
        from datetime import datetime

        if isinstance(dt, datetime):
            return dt.isoformat() + "Z"
    except Exception:
        pass
    return str(dt)


def parse_float_safe(value: Any, default: float = 0.0) -> float:
    """Safely parse a value to float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_int_safe(value: Any, default: int = 0) -> int:
    """Safely parse a value to int."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
