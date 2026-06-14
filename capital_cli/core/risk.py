"""Risk engine and preview cache for trade validation."""

import logging
import math
from datetime import datetime, timezone
from typing import Any

from .config import get_config
from .errors import (
    ConfirmRequiredError,
    DryRunError,
    PreviewError,
    RiskLimitError,
    TradingDisabledError,
)
from .http_client import get_client
from .models import (
    Direction,
    PreviewPositionRequest,
    PreviewResult,
    PreviewWorkingOrderRequest,
    RiskCheck,
)
from .state import get_state_store

logger = logging.getLogger(__name__)


def _safe_positive_float(value: Any, default: float) -> float:
    """Coerce a broker-supplied value to a finite, positive float.

    Returns ``default`` when ``value`` is None/missing, not a real number, or
    non-finite/non-positive (NaN, inf, <= 0). This keeps malformed dealing-rules
    from poisoning the size math with TypeError/ValueError/ZeroDivisionError.
    """
    try:
        coerced = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(coerced) or coerced <= 0:
        return default
    return coerced


def _extract_rule_value(rules: dict[str, Any], key: str, default: float) -> float:
    """Pull ``rules[key]["value"]`` defensively (the rule or its value may be null)."""
    rule = rules.get(key)
    raw = rule.get("value") if isinstance(rule, dict) else None
    return _safe_positive_float(raw, default)


class RiskEngine:
    """
    Risk engine for trade validation and preview caching.

    Implements:
    - Trading enable/disable checks
    - Epic allowlist validation
    - Size limit validation
    - Position/order count limits
    - Preview cache with TTL
    - Size normalization
    """

    def __init__(self) -> None:
        self.config = get_config()
        self.client = get_client()
        self.state = get_state_store()

        # Preview cache: {preview_id: PreviewResult} (in-process fast path;
        # the persistent copy in StateStore is the source of truth)
        self._preview_cache: dict[str, PreviewResult] = {}

    def _check_daily_limit(self) -> RiskCheck:
        """Check if daily order limit is reached (persisted across invocations)."""
        # The trading "day" is the UTC day (matches the broker's server time).
        today = datetime.now(timezone.utc).date().isoformat()
        count = self.state.get_order_count(today)

        if count >= self.config.cap_max_orders_per_day:
            return RiskCheck(
                check="daily_order_limit",
                passed=False,
                message=f"Daily order limit reached ({self.config.cap_max_orders_per_day})",
            )

        return RiskCheck(
            check="daily_order_limit",
            passed=True,
            message=f"Daily orders: {count}/{self.config.cap_max_orders_per_day}",
        )

    def increment_order_count(self) -> None:
        """Increment the persisted daily order counter."""
        # The trading "day" is the UTC day (matches the broker's server time).
        today = datetime.now(timezone.utc).date().isoformat()
        self.state.increment_order_count(today)

    async def _get_market_details(self, epic: str) -> dict[str, Any]:
        """Fetch market details including dealing rules."""
        response = await self.client.get(f"/markets/{epic}")
        return response.json()

    def _validate_size(
        self,
        size: float,
        min_size: float,
        max_size: float,
        increment: float,
        *,
        auto_normalize: bool,
    ) -> tuple[float, RiskCheck]:
        """Validate the requested size against broker dealing rules WITHOUT silently
        changing it.

        Returns (effective_size, check). The effective size equals the requested
        size, except that increment misalignment is rounded ONLY when auto_normalize
        is True. Sizes below the broker minimum or above the broker maximum always
        fail (they are never silently clamped to the boundary).
        """
        if size < min_size:
            return size, RiskCheck(
                check="size",
                passed=False,
                message=f"Size {size} is below the broker minimum {min_size}. Use at least {min_size}.",
            )
        if size > max_size:
            return size, RiskCheck(
                check="size",
                passed=False,
                message=f"Size {size} is above the broker maximum {max_size}. Use at most {max_size}.",
            )
        # Guard the increment math: a missing/zero/negative/non-finite increment
        # means "no increment constraint", so the size passes as-is.
        if not math.isfinite(increment) or increment <= 0:
            return size, RiskCheck(check="size", passed=True, message=f"Size {size} is valid.")
        rounded = round(size / increment) * increment
        tol = max(increment * 1e-4, 1e-9)
        if abs(rounded - size) <= tol:
            return size, RiskCheck(check="size", passed=True, message=f"Size {size} is valid.")
        if not auto_normalize:
            return size, RiskCheck(
                check="size",
                passed=False,
                message=(
                    f"Size {size} is not a multiple of the broker increment {increment}. "
                    f"Nearest valid size is {rounded}. Re-run with --auto-normalize-size to use {rounded}."
                ),
            )
        if rounded < min_size or rounded > max_size:
            return size, RiskCheck(
                check="size",
                passed=False,
                message=f"Size {size} rounds to {rounded}, outside the broker range [{min_size}, {max_size}].",
            )
        return rounded, RiskCheck(
            check="size",
            passed=True,
            message=f"Size normalized from {size} to {rounded} (increment {increment}).",
        )

    def check_open_position_limit(self, count: int) -> None:
        """Reject execution when the account already holds the maximum open positions.

        The risk engine never makes HTTP calls, so the caller (the execute-position
        command) supplies the current open-position count.

        Raises:
            RiskLimitError: If ``count`` is already at or above cap_max_open_positions.
        """
        limit = self.config.cap_max_open_positions
        if count >= limit:
            raise RiskLimitError(
                f"Open position limit reached ({count}/{limit}). "
                "Close a position or raise CAP_MAX_OPEN_POSITIONS.",
                details={"open_positions": count, "limit": limit},
            )

    async def preview_position(
        self,
        request: PreviewPositionRequest,
        *,
        size_policy_limit: float | None = None,
        size_policy_label: str = "max_position_size",
    ) -> PreviewResult:
        """
        Preview a position and validate against risk policy.

        Args:
            request: Position preview request
            size_policy_limit: Policy size ceiling to enforce. Defaults to
                cap_max_position_size; working-order previews pass
                cap_max_working_order_size instead.
            size_policy_label: Check name/label for the size-policy ceiling.

        Returns:
            Preview result with checks and normalized values
        """
        if size_policy_limit is None:
            size_policy_limit = self.config.cap_max_position_size
        checks: list[RiskCheck] = []

        # Check 1: Trading enabled
        if not self.config.cap_allow_trading:
            checks.append(
                RiskCheck(
                    check="trading_enabled",
                    passed=False,
                    message="Trading is disabled (CAP_ALLOW_TRADING=false)",
                )
            )
            return PreviewResult(
                normalized_request={},
                checks=checks,
                all_checks_passed=False,
            )

        checks.append(RiskCheck(check="trading_enabled", passed=True, message="Trading is enabled"))

        # Check 2: Epic allowlist
        if not self.config.is_epic_allowed(request.epic):
            checks.append(
                RiskCheck(
                    check="epic_allowed",
                    passed=False,
                    message=f"Epic '{request.epic}' not in allowlist",
                )
            )
            return PreviewResult(
                normalized_request={},
                checks=checks,
                all_checks_passed=False,
            )

        checks.append(
            RiskCheck(
                check="epic_allowed", passed=True, message=f"Epic '{request.epic}' is allowed"
            )
        )

        # Check 3: Daily order limit
        daily_check = self._check_daily_limit()
        checks.append(daily_check)

        if not daily_check.passed:
            return PreviewResult(
                normalized_request={},
                checks=checks,
                all_checks_passed=False,
            )

        # Fetch market details
        try:
            market_data = await self._get_market_details(request.epic)
        except Exception as e:
            logger.error(f"Failed to fetch market details for {request.epic}: {e}")
            checks.append(
                RiskCheck(
                    check="market_details",
                    passed=False,
                    message=f"Failed to fetch market details: {str(e)}",
                )
            )
            return PreviewResult(
                normalized_request={},
                checks=checks,
                all_checks_passed=False,
            )

        checks.append(
            RiskCheck(check="market_details", passed=True, message="Market details fetched")
        )

        # Extract dealing rules (broker values may be null/missing/non-finite)
        dealing_rules = market_data.get("dealingRules")
        if not isinstance(dealing_rules, dict):
            dealing_rules = {}
        min_deal_size = _extract_rule_value(dealing_rules, "minDealSize", 0.1)
        max_deal_size = _extract_rule_value(dealing_rules, "maxDealSize", 1000.0)
        min_size_increment = _extract_rule_value(dealing_rules, "minSizeIncrement", 0.1)

        # Check 4: Validate size against broker dealing rules (no silent changes)
        effective_size, size_check = self._validate_size(
            request.size,
            min_deal_size,
            max_deal_size,
            min_size_increment,
            auto_normalize=request.auto_normalize_size,
        )
        checks.append(size_check)
        if not size_check.passed:
            return PreviewResult(
                normalized_request={"requested_size": request.size},
                checks=checks,
                all_checks_passed=False,
            )

        # Check 5: Max size policy (position vs working-order limit, per caller)
        if effective_size > size_policy_limit:
            checks.append(
                RiskCheck(
                    check=size_policy_label,
                    passed=False,
                    message=f"Size {effective_size} exceeds policy limit {size_policy_limit}",
                )
            )
            return PreviewResult(
                normalized_request={},
                checks=checks,
                all_checks_passed=False,
            )

        checks.append(
            RiskCheck(
                check=size_policy_label,
                passed=True,
                message=f"Size {effective_size} within limit {size_policy_limit}",
            )
        )

        # Build normalized request (mode='json' to serialize enums as strings)
        normalized_request = request.model_dump(mode="json")
        normalized_request["size"] = effective_size

        # Extract snapshot for entry price estimate
        snapshot = market_data.get("snapshot", {})
        estimated_entry = None
        if request.direction == Direction.BUY:
            estimated_entry = snapshot.get("offer")
        else:
            estimated_entry = snapshot.get("bid")

        # Create preview result
        result = PreviewResult(
            normalized_request=normalized_request,
            checks=checks,
            all_checks_passed=all(c.passed for c in checks),
            estimated_entry=estimated_entry,
            estimated_risk_notes="Preview only; actual execution may differ based on market conditions.",
        )

        # Cache the preview
        self._preview_cache[result.preview_id] = result
        self.state.save_preview(result)
        logger.info(f"Created preview {result.preview_id} for {request.epic}")

        return result

    async def preview_working_order(self, request: PreviewWorkingOrderRequest) -> PreviewResult:
        """Preview a working order (similar to position preview)."""
        # Convert to position request for validation
        position_request = PreviewPositionRequest(
            epic=request.epic,
            direction=request.direction,
            size=request.size,
            guaranteed_stop=request.guaranteed_stop,
            trailing_stop=request.trailing_stop,
            stop_level=request.stop_level,
            stop_distance=request.stop_distance,
            stop_amount=request.stop_amount,
            profit_level=request.profit_level,
            profit_distance=request.profit_distance,
            profit_amount=request.profit_amount,
            auto_normalize_size=request.auto_normalize_size,
        )

        # Run position checks, but enforce the working-order size ceiling.
        result = await self.preview_position(
            position_request,
            size_policy_limit=self.config.cap_max_working_order_size,
            size_policy_label="max_working_order_size",
        )

        # Add working order specific fields
        if result.all_checks_passed:
            result.normalized_request["type"] = request.type.value
            result.normalized_request["level"] = request.level
            if request.good_till_date:
                result.normalized_request["good_till_date"] = request.good_till_date

        return result

    def get_preview(self, preview_id: str) -> PreviewResult:
        """
        Get a cached preview result.

        Args:
            preview_id: Preview ID

        Returns:
            Preview result

        Raises:
            PreviewError: If preview not found or expired
        """
        preview = self._preview_cache.get(preview_id)
        if preview is None:
            preview = self.state.load_preview(preview_id)

        if not preview:
            raise PreviewError(f"Preview {preview_id} not found", code="PREVIEW_NOT_FOUND")

        if preview.is_expired(self.config.cap_preview_cache_ttl_s):
            self._preview_cache.pop(preview_id, None)
            self.state.delete_preview(preview_id)
            raise PreviewError(f"Preview {preview_id} expired", code="PREVIEW_EXPIRED")

        return preview

    def validate_execution_guards(self, *, confirm: bool, preview_id: str | None = None) -> None:
        """
        Validate execution guards before trade execution.

        Args:
            confirm: Explicit confirmation flag
            preview_id: Optional preview ID to validate

        Raises:
            TradingDisabledError: If trading is disabled
            DryRunError: If dry-run mode is enabled
            ConfirmRequiredError: If confirmation is required but not provided
            PreviewError: If preview not found or checks failed
        """
        # Guard 1: Trading enabled
        if not self.config.cap_allow_trading:
            raise TradingDisabledError()

        # Guard 2: Dry-run mode
        if self.config.cap_dry_run:
            raise DryRunError()

        # Guard 3: Explicit confirmation
        if self.config.cap_require_explicit_confirm and not confirm:
            raise ConfirmRequiredError()

        # Guard 4: Preview validation
        if preview_id:
            preview = self.get_preview(preview_id)
            if not preview.all_checks_passed:
                raise PreviewError(
                    "Preview checks failed, cannot execute",
                    code="PREVIEW_CHECKS_FAILED",
                )

    def validate_mutation_guards(self, *, confirm: bool) -> None:
        """Validate guards for account/settings mutations (not trade execution).

        Unlike trade execution, this does NOT require CAP_ALLOW_TRADING — changing
        account preferences is risk-sensitive but is not opening or closing a trade.
        Still blocked by dry-run mode and the explicit-confirm requirement.

        Raises:
            DryRunError: If dry-run mode is enabled.
            ConfirmRequiredError: If confirmation is required but not provided.
        """
        if self.config.cap_dry_run:
            raise DryRunError()
        if self.config.cap_require_explicit_confirm and not confirm:
            raise ConfirmRequiredError()


# Global risk engine instance
_risk_engine: RiskEngine | None = None


def get_risk_engine() -> RiskEngine:
    """Get or create the global risk engine instance."""
    global _risk_engine
    if _risk_engine is None:
        _risk_engine = RiskEngine()
    return _risk_engine


def reset_risk_engine() -> None:
    """Reset the global risk engine (mainly for testing)."""
    global _risk_engine
    _risk_engine = None
