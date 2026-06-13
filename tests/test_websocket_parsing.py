"""Offline regression tests for WebSocketClient._parse_message.

These tests construct WebSocketClient() directly without connecting to any
network. The autouse `_credentials` fixture in tests/conftest.py provides
fake credentials so get_config() resolves successfully.
"""

import asyncio
import json
from unittest.mock import MagicMock

from capital_cli.core.models import OHLCBar, PriceTick, SessionTokens
from capital_cli.core.websocket_client import WebSocketClient


def test_parse_message_valid_quote_maps_ofr_to_offer():
    client = WebSocketClient()
    message = json.dumps(
        {
            "destination": "quote",
            "payload": {
                "epic": "BTCUSD",
                "bid": 100.0,
                "ofr": 101.0,
                "bidQty": 1.0,
                "ofrQty": 1.0,
                "timestamp": 1234567890,
            },
        }
    )

    tick = client._parse_message(message)

    assert isinstance(tick, PriceTick)
    assert tick.epic == "BTCUSD"
    assert tick.bid == 100.0
    assert tick.offer == 101.0


def test_parse_message_non_quote_destination_returns_none():
    client = WebSocketClient()
    message = json.dumps({"destination": "marketData.subscribe", "status": "OK"})

    assert client._parse_message(message) is None


def test_parse_message_malformed_json_returns_none():
    client = WebSocketClient()

    assert client._parse_message("not valid json") is None


def test_parse_message_quote_missing_ofr_and_bid_returns_none():
    client = WebSocketClient()
    message = json.dumps(
        {
            "destination": "quote",
            "payload": {"epic": "BTCUSD", "timestamp": 1234567890},
        }
    )

    assert client._parse_message(message) is None


def test_parse_ohlc_valid_wrapped():
    client = WebSocketClient()
    msg = json.dumps(
        {
            "destination": "ohlc.event",
            "payload": {
                "epic": "BTCUSD",
                "resolution": "MINUTE",
                "type": "classic",
                "priceType": "bid",
                "t": 1700000000000,
                "o": 1.0,
                "h": 2.0,
                "l": 0.5,
                "c": 1.5,
            },
        }
    )
    bar = client._parse_ohlc(msg)
    assert isinstance(bar, OHLCBar)
    assert bar.epic == "BTCUSD"
    assert (bar.open, bar.high, bar.low, bar.close) == (1.0, 2.0, 0.5, 1.5)
    assert bar.resolution == "MINUTE"
    assert bar.type == "classic"


def test_parse_ohlc_flat_fallback():
    client = WebSocketClient()
    msg = json.dumps(
        {
            "destination": "ohlc.event",
            "epic": "BTCUSD",
            "resolution": "HOUR",
            "type": "classic",
            "priceType": "bid",
            "t": 1700000000000,
            "o": 1.0,
            "h": 2.0,
            "l": 0.5,
            "c": 1.5,
        }
    )
    bar = client._parse_ohlc(msg)
    assert isinstance(bar, OHLCBar)
    assert bar.resolution == "HOUR"


def test_parse_ohlc_non_event_returns_none():
    client = WebSocketClient()
    assert client._parse_ohlc(json.dumps({"destination": "quote", "payload": {}})) is None
    assert client._parse_ohlc("not json") is None


def test_parse_ohlc_missing_fields_returns_none():
    client = WebSocketClient()
    msg = json.dumps({"destination": "ohlc.event", "payload": {"epic": "BTCUSD", "o": 1.0}})
    assert client._parse_ohlc(msg) is None


def test_parse_ohlc_infinite_timestamp_does_not_raise():
    client = WebSocketClient()
    # json.loads accepts Infinity by default; a bad timestamp must not crash the parser.
    msg = '{"destination": "ohlc.event", "payload": {"epic": "BTCUSD", "resolution": "MINUTE", "t": Infinity, "o": 1.0, "h": 2.0, "l": 0.5, "c": 1.5}}'
    result = client._parse_ohlc(msg)  # must not raise
    # With a fallback timestamp the bar parses fine; the point is no exception escaped.
    from capital_cli.core.models import OHLCBar
    assert result is None or isinstance(result, OHLCBar)


def test_send_ping_uses_application_message():
    client = WebSocketClient()
    sent: list[str] = []

    class _WS:
        async def send(self, m):
            sent.append(m)

        async def ping(self):
            sent.append("PROTOCOL_PING")

    client._ws = _WS()
    client.session_manager = MagicMock()
    client.session_manager.client.session_tokens = SessionTokens(cst="C", x_security_token="X")

    asyncio.run(client._send_ping())

    assert len(sent) == 1
    msg = json.loads(sent[0])
    assert msg["destination"] == "ping"
    assert msg["cst"] == "C"
    assert msg["securityToken"] == "X"
