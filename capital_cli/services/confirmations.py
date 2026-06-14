"""Broker confirmation polling and request-body construction (presentation-free)."""

from __future__ import annotations

from typing import Any

from capital_cli.core.http_client import get_client
from capital_cli.core.utils import poll_until


async def get_confirmation(deal_reference: str) -> dict[str, Any]:
    """Read GET /confirms/{dealReference} once and return the parsed JSON.

    Single-shot counterpart to :func:`wait_for_confirmation`. Unlike the wait
    path, this does NOT normalize ``dealStatus`` to ``status`` — it returns the
    broker payload verbatim, matching the CLI's historical non-wait behavior.
    """
    client = get_client()
    return (await client.get(f"/confirms/{deal_reference}")).json()


async def wait_for_confirmation(
    deal_reference: str, timeout_s: float, poll_interval_ms: int = 500
) -> dict[str, Any]:
    """Poll GET /confirms/{dealReference} until the broker accepts or rejects the deal.

    The Capital.com API reports the broker's decision in the ``dealStatus``
    field (ACCEPTED/REJECTED); ``status`` is the resulting position/order
    lifecycle state (e.g. OPEN, CLOSED) and is not a useful done-condition.
    The returned dict normalizes ``status`` to the ``dealStatus`` value so
    callers can uniformly check ``confirmation["status"]``.
    """
    client = get_client()

    async def check() -> dict[str, Any]:
        return (await client.get(f"/confirms/{deal_reference}")).json()

    def done(data: dict[str, Any]) -> bool:
        return data.get("dealStatus") in ("ACCEPTED", "REJECTED")

    result = await poll_until(check, done, timeout_s=timeout_s, poll_interval_ms=poll_interval_ms)
    if result is None:
        return {
            "status": "TIMEOUT",
            "message": f"Confirmation timed out after {timeout_s}s",
        }
    if "dealStatus" in result:
        result = {**result, "status": result["dealStatus"]}
    return result


def mutation_status(data: dict[str, Any]) -> str:
    """Derive an audit status string from a broker mutation response.

    Prefers the confirmation's normalized ``status`` (ACCEPTED/REJECTED/TIMEOUT),
    then a top-level ``dealStatus``, then ``status``, else ``SUBMITTED``.
    """
    confirmation = data.get("confirmation")
    if isinstance(confirmation, dict) and confirmation.get("status"):
        return str(confirmation["status"])
    if data.get("dealStatus"):
        return str(data["dealStatus"])
    if data.get("status"):
        return str(data["status"])
    return "SUBMITTED"


def build_broker_request(
    normalized: dict[str, Any], *, include_order_fields: bool
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "epic": normalized["epic"],
        "direction": normalized["direction"],
        "size": normalized["size"],
    }
    if include_order_fields:
        body["type"] = normalized["type"]
        body["level"] = normalized["level"]
        if normalized.get("good_till_date"):
            body["goodTillDate"] = normalized["good_till_date"]
    if normalized.get("guaranteed_stop"):
        body["guaranteedStop"] = True
    if normalized.get("trailing_stop"):
        body["trailingStop"] = True
    for src, dst in [
        ("stop_level", "stopLevel"),
        ("stop_distance", "stopDistance"),
        ("stop_amount", "stopAmount"),
        ("profit_level", "profitLevel"),
        ("profit_distance", "profitDistance"),
        ("profit_amount", "profitAmount"),
    ]:
        if normalized.get(src) is not None:
            body[dst] = normalized[src]
    return body
