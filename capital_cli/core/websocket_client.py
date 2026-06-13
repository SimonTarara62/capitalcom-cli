"""WebSocket client for Capital.com streaming API."""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any, Optional

import websockets
from websockets.asyncio.client import ClientConnection

from .config import get_config
from .errors import SessionError, UpstreamError
from .models import OHLCBar, PriceTick
from .session import get_session_manager

logger = logging.getLogger(__name__)


def _ms_to_iso(ms: Any) -> str:
    """Convert an epoch-milliseconds value to an ISO 8601 'Z' timestamp."""
    if ms is None:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        return datetime.fromtimestamp(float(ms) / 1000, tz=timezone.utc).isoformat().replace(
            "+00:00", "Z"
        )
    except (TypeError, ValueError, OSError):
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# Singleton instance
_websocket_client: Optional["WebSocketClient"] = None


def get_websocket_client() -> "WebSocketClient":
    """Get or create WebSocket client singleton."""
    global _websocket_client
    if _websocket_client is None:
        _websocket_client = WebSocketClient()
    return _websocket_client


class WebSocketClient:
    """
    WebSocket client for Capital.com streaming API.

    Handles real-time price streaming with authentication, subscription management,
    and automatic reconnection.
    """

    def __init__(self):
        self.config = get_config()
        self.session_manager = get_session_manager()
        self._ws: ClientConnection | None = None
        self._subscribed_epics: set[str] = set()
        self._subscribed_ohlc: set[str] = set()
        self._ohlc_params: tuple[list[str], list[str], str] | None = None
        self._last_ping: datetime | None = None

    async def __aenter__(self) -> "WebSocketClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def connect(self) -> None:
        """
        Connect to Capital.com WebSocket API.

        Raises:
            SessionError: If WebSocket is disabled or authentication fails
            UpstreamError: If connection fails
        """
        if not self.config.cap_ws_enabled:
            raise SessionError(
                "WebSocket streaming is disabled. Set CAP_WS_ENABLED=true to enable."
            )

        # Ensure we have valid session tokens
        await self.session_manager.ensure_logged_in()
        status = self.session_manager.get_status()

        if not status.logged_in or not self.session_manager.client.session_tokens:
            raise SessionError("Not logged in. Cannot establish WebSocket connection.")

        tokens = self.session_manager.client.session_tokens
        ws_url = self.config.ws_url

        try:
            logger.info(f"Connecting to WebSocket: {ws_url}")

            # Connect with authentication headers
            self._ws = await websockets.connect(
                ws_url,
                additional_headers={
                    "CST": tokens.cst,
                    "X-SECURITY-TOKEN": tokens.x_security_token,
                },
                ping_interval=None,  # We'll handle pings manually
                close_timeout=5,
            )

            self._last_ping = datetime.now(timezone.utc)
            logger.info("WebSocket connected successfully")

        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            raise UpstreamError(f"Failed to connect to WebSocket: {e}") from e

    async def close(self) -> None:
        """Close WebSocket connection."""
        if self._ws:
            logger.info("Closing WebSocket connection")
            await self._ws.close()
            self._ws = None
            self._subscribed_epics.clear()
            self._subscribed_ohlc.clear()
            self._ohlc_params = None
            self._last_ping = None

    async def subscribe(self, epics: list[str]) -> None:
        """
        Subscribe to price updates for given EPICs.

        Args:
            epics: List of market EPICs (max 40 per Capital.com limits)

        Raises:
            ValueError: If too many EPICs requested
            SessionError: If not connected
        """
        if len(epics) > 40:
            raise ValueError(f"Cannot subscribe to more than 40 EPICs (requested: {len(epics)})")

        if not self._ws:
            raise SessionError("WebSocket not connected. Call connect() first.")

        tokens = self.session_manager.client.session_tokens
        if not tokens:
            raise SessionError("Not logged in. Cannot subscribe.")

        # Capital.com streaming API: a single marketData.subscribe message
        # carrying the session tokens and the full list of EPICs.
        subscribe_msg = {
            "destination": "marketData.subscribe",
            "correlationId": "1",
            "cst": tokens.cst,
            "securityToken": tokens.x_security_token,
            "payload": {"epics": epics},
        }

        try:
            await self._ws.send(json.dumps(subscribe_msg))
            self._subscribed_epics.update(epics)
            logger.debug(f"Subscribed to {epics}")
        except Exception as e:
            logger.error(f"Failed to subscribe to {epics}: {e}")
            raise UpstreamError(f"Subscription failed for {epics}: {e}") from e

    async def unsubscribe(self, epics: list[str]) -> None:
        """
        Unsubscribe from price updates.

        Args:
            epics: List of market EPICs to unsubscribe from
        """
        if not self._ws:
            return

        to_remove = [epic for epic in epics if epic in self._subscribed_epics]
        if not to_remove:
            return

        tokens = self.session_manager.client.session_tokens
        if not tokens:
            return

        unsubscribe_msg = {
            "destination": "marketData.unsubscribe",
            "correlationId": "2",
            "cst": tokens.cst,
            "securityToken": tokens.x_security_token,
            "payload": {"epics": to_remove},
        }

        try:
            await self._ws.send(json.dumps(unsubscribe_msg))
            for epic in to_remove:
                self._subscribed_epics.discard(epic)
            logger.debug(f"Unsubscribed from {to_remove}")
        except Exception as e:
            logger.warning(f"Failed to unsubscribe from {to_remove}: {e}")

    async def subscribe_ohlc(
        self, epics: list[str], resolutions: list[str], bar_type: str = "classic"
    ) -> None:
        """Subscribe to OHLC candlestick updates for the given EPICs/resolutions."""
        if len(epics) > 40:
            raise ValueError(f"Cannot subscribe to more than 40 EPICs (requested: {len(epics)})")
        if not self._ws:
            raise SessionError("WebSocket not connected. Call connect() first.")
        tokens = self.session_manager.client.session_tokens
        if not tokens:
            raise SessionError("Not logged in. Cannot subscribe.")

        msg = {
            "destination": "OHLCMarketData.subscribe",
            "correlationId": "3",
            "cst": tokens.cst,
            "securityToken": tokens.x_security_token,
            "payload": {"epics": epics, "resolutions": resolutions, "type": bar_type},
        }
        try:
            await self._ws.send(json.dumps(msg))
            self._ohlc_params = (epics, resolutions, bar_type)
            for epic in epics:
                for res in resolutions:
                    self._subscribed_ohlc.add(f"{epic}:{res}:{bar_type}")
            logger.debug(f"Subscribed OHLC {epics} {resolutions} {bar_type}")
        except Exception as e:
            logger.error(f"Failed to subscribe OHLC {epics}: {e}")
            raise UpstreamError(f"OHLC subscription failed for {epics}: {e}") from e

    async def unsubscribe_ohlc(self) -> None:
        """Unsubscribe from all current OHLC subscriptions."""
        if not self._ws or not self._ohlc_params:
            return
        tokens = self.session_manager.client.session_tokens
        if not tokens:
            return
        epics, resolutions, bar_type = self._ohlc_params
        msg = {
            "destination": "OHLCMarketData.unsubscribe",
            "correlationId": "4",
            "cst": tokens.cst,
            "securityToken": tokens.x_security_token,
            "payload": {"epics": epics, "resolutions": resolutions, "types": [bar_type]},
        }
        try:
            await self._ws.send(json.dumps(msg))
            self._subscribed_ohlc.clear()
            self._ohlc_params = None
            logger.debug("Unsubscribed OHLC")
        except Exception as e:  # noqa: BLE001 - unsubscribe failure is non-fatal
            logger.warning(f"Failed to unsubscribe OHLC: {e}")

    def _parse_ohlc(self, message: str | bytes) -> OHLCBar | None:
        """Parse an OHLC candlestick event message; return None for anything else."""
        try:
            data = json.loads(message)
        except (json.JSONDecodeError, ValueError):
            return None
        if not isinstance(data, dict) or data.get("destination") != "ohlc.event":
            return None
        raw_payload = data.get("payload")
        payload: dict[str, Any] = raw_payload if isinstance(raw_payload, dict) else data
        epic = payload.get("epic")
        if not epic or not all(k in payload for k in ("o", "h", "l", "c")):
            return None
        try:
            return OHLCBar(
                epic=epic,
                resolution=str(payload.get("resolution", "MINUTE")),
                type=str(payload.get("type", "classic")),
                price_type=str(payload.get("priceType", "bid")),
                timestamp=_ms_to_iso(payload.get("t")),
                open=float(payload["o"]),
                high=float(payload["h"]),
                low=float(payload["l"]),
                close=float(payload["c"]),
            )
        except (TypeError, ValueError):
            return None

    async def stream_ohlc(
        self, duration: float = 300.0, reconnect_attempts: int = 3
    ) -> AsyncIterator[OHLCBar]:
        """Stream OHLC candlestick bars (parallel to stream(); yields OHLCBar)."""
        if not self._ws:
            raise SessionError("WebSocket not connected. Call connect() first.")

        start_time = datetime.now(timezone.utc)
        reconnect_count = 0
        try:
            while True:
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                if elapsed >= duration:
                    logger.info(f"OHLC stream duration {duration}s reached, stopping")
                    break

                if await self._should_ping():
                    await self._send_ping()

                try:
                    timeout = min(duration - elapsed, 10.0)
                    message = await asyncio.wait_for(self._ws.recv(), timeout=timeout)
                    bar = self._parse_ohlc(message)
                    if bar:
                        yield bar
                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    if reconnect_count < reconnect_attempts:
                        reconnect_count += 1
                        logger.warning(
                            f"WebSocket disconnected, reconnecting "
                            f"({reconnect_count}/{reconnect_attempts})"
                        )
                        await asyncio.sleep(2**reconnect_count)
                        params = self._ohlc_params
                        await self.close()
                        await self.connect()
                        if params:
                            await self.subscribe_ohlc(*params)
                        logger.info("Reconnection successful")
                    else:
                        logger.error(
                            f"Max reconnection attempts ({reconnect_attempts}) reached"
                        )
                        raise UpstreamError(
                            "WebSocket connection lost and reconnection failed"
                        ) from None
        finally:
            if self._ohlc_params:
                await self.unsubscribe_ohlc()

    async def _send_ping(self) -> None:
        """Keep the connection alive using the documented application-level ping.

        Capital.com's streaming session is kept alive by a JSON ``ping`` message
        carrying the session tokens (not just a transport-level PING frame). Falls
        back to a transport ping only if tokens are unavailable.
        """
        if not self._ws:
            return
        tokens = self.session_manager.client.session_tokens
        try:
            if tokens:
                ping_msg = {
                    "destination": "ping",
                    "correlationId": "ping",
                    "cst": tokens.cst,
                    "securityToken": tokens.x_security_token,
                }
                await self._ws.send(json.dumps(ping_msg))
            else:
                await self._ws.ping()
            self._last_ping = datetime.now(timezone.utc)
            logger.debug("Sent keep-alive ping")
        except Exception as e:  # noqa: BLE001 - ping failure is non-fatal
            logger.warning(f"Failed to send ping: {e}")

    async def _should_ping(self) -> bool:
        """Check if we should send a ping (every 5 minutes)."""
        if not self._last_ping:
            return True

        elapsed = (datetime.now(timezone.utc) - self._last_ping).total_seconds()
        return elapsed >= 300  # 5 minutes

    def _parse_message(self, message: str | bytes) -> PriceTick | None:
        """
        Parse incoming WebSocket message.

        Args:
            message: Raw JSON message from WebSocket

        Returns:
            PriceTick if it's a price update, None otherwise
        """
        try:
            data = json.loads(message)

            # Check if it's a price update message
            # Capital.com format: {"status": "OK", "destination": "quote",
            # "payload": {"epic": ..., "bid": ..., "ofr": ..., "timestamp": ...}}
            if isinstance(data, dict) and data.get("destination") == "quote":
                payload = data.get("payload", {})
                epic = payload.get("epic")

                if epic and "bid" in payload and "ofr" in payload:
                    return PriceTick(
                        epic=epic,
                        bid=float(payload["bid"]),
                        offer=float(payload["ofr"]),
                        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                        change_percent=payload.get("changePercent")
                    )

            # Heartbeat or other message types
            return None

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse WebSocket message: {e}")
            return None

    async def stream(
        self,
        duration: float = 300.0,
        reconnect_attempts: int = 3
    ) -> AsyncIterator[PriceTick]:
        """
        Stream price updates.

        Args:
            duration: Stream duration in seconds (default: 5 minutes)
            reconnect_attempts: Number of reconnection attempts on disconnect

        Yields:
            PriceTick objects as they arrive

        Raises:
            SessionError: If not connected
            UpstreamError: If connection fails after retries
        """
        if not self._ws:
            raise SessionError("WebSocket not connected. Call connect() first.")

        start_time = datetime.now(timezone.utc)
        reconnect_count = 0

        try:
            while True:
                # Check duration timeout
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                if elapsed >= duration:
                    logger.info(f"Stream duration {duration}s reached, stopping")
                    break

                # Send ping if needed
                if await self._should_ping():
                    await self._send_ping()

                try:
                    # Receive message with timeout
                    remaining = duration - elapsed
                    timeout = min(remaining, 10.0)  # Max 10s wait per message

                    message = await asyncio.wait_for(
                        self._ws.recv(),
                        timeout=timeout
                    )

                    # Parse and yield price tick
                    tick = self._parse_message(message)
                    if tick:
                        yield tick

                except asyncio.TimeoutError:
                    # No message received, continue (normal for quiet periods)
                    continue

                except websockets.exceptions.ConnectionClosed:
                    # Connection lost, attempt reconnection
                    if reconnect_count < reconnect_attempts:
                        reconnect_count += 1
                        logger.warning(f"WebSocket disconnected, reconnecting ({reconnect_count}/{reconnect_attempts})")

                        await asyncio.sleep(2 ** reconnect_count)  # Exponential backoff

                        # Reconnect and resubscribe
                        epics_to_restore = list(self._subscribed_epics)
                        await self.close()
                        await self.connect()
                        await self.subscribe(epics_to_restore)

                        logger.info("Reconnection successful")
                    else:
                        logger.error(f"Max reconnection attempts ({reconnect_attempts}) reached")
                        raise UpstreamError("WebSocket connection lost and reconnection failed") from None

        finally:
            # Cleanup: unsubscribe from all EPICs
            if self._subscribed_epics:
                await self.unsubscribe(list(self._subscribed_epics))
