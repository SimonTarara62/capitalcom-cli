"""Offline regression tests for WebSocketClient._parse_message.

These tests construct WebSocketClient() directly without connecting to any
network. The autouse `_credentials` fixture in tests/conftest.py provides
fake credentials so get_config() resolves successfully.
"""

import json

from capital_cli.core.models import PriceTick
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
