"""poll_until must let non-transient errors propagate, not mask them as TIMEOUT."""

import asyncio

import httpx
import pytest

from capital_cli.core.errors import UpstreamError
from capital_cli.core.utils import poll_until


async def test_poll_until_propagates_non_transient_error():
    async def fn():
        raise UpstreamError("broker rejected", status_code=400)

    with pytest.raises(UpstreamError):
        await poll_until(
            fn, lambda r: True, timeout_s=2.0, poll_interval_ms=50, initial_delay_ms=0
        )


async def test_poll_until_swallows_transient_then_times_out():
    async def fn():
        raise httpx.ConnectError("network blip")

    # Transient errors are swallowed; with no success the call times out.
    result = await poll_until(
        fn, lambda r: True, timeout_s=0.3, poll_interval_ms=50, initial_delay_ms=0
    )
    assert result is None


async def test_poll_until_returns_result_on_success():
    calls = {"n": 0}

    async def fn():
        calls["n"] += 1
        return calls["n"]

    result = await poll_until(
        fn, lambda r: r >= 2, timeout_s=2.0, poll_interval_ms=50, initial_delay_ms=0
    )
    assert result == 2


async def test_poll_until_swallows_asyncio_timeout():
    async def fn():
        raise asyncio.TimeoutError()

    result = await poll_until(
        fn, lambda r: True, timeout_s=0.3, poll_interval_ms=50, initial_delay_ms=0
    )
    assert result is None
