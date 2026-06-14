from capital_cli.services.confirmations import (
    build_broker_request,
    get_confirmation,
    mutation_status,
)


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class _RecordingClient:
    def __init__(self, payload):
        self._payload = payload
        self.calls: list[str] = []

    async def get(self, path):
        self.calls.append(path)
        return _Resp(self._payload)


async def test_get_confirmation_hits_endpoint_and_returns_json(monkeypatch):
    payload = {"dealStatus": "ACCEPTED", "dealReference": "o_ref123"}
    client = _RecordingClient(payload)
    monkeypatch.setattr(
        "capital_cli.services.confirmations.get_client", lambda: client
    )

    result = await get_confirmation("o_ref123")

    assert client.calls == ["/confirms/o_ref123"]
    # Single-shot path returns the broker payload verbatim (no status normalization).
    assert result == payload


def test_build_keeps_zero_valued_fields():
    body = build_broker_request(
        {"epic": "GOLD", "direction": "BUY", "size": 1.0, "stop_level": 0.0},
        include_order_fields=False,
    )
    assert body["stopLevel"] == 0.0


def test_build_order_fields():
    body = build_broker_request(
        {"epic": "G", "direction": "BUY", "size": 1.0, "type": "LIMIT", "level": 100.0},
        include_order_fields=True,
    )
    assert body["type"] == "LIMIT"
    assert body["level"] == 100.0


def test_mutation_status_prefers_confirmation():
    assert mutation_status({"confirmation": {"status": "ACCEPTED"}}) == "ACCEPTED"
    assert mutation_status({"dealStatus": "REJECTED"}) == "REJECTED"
    assert mutation_status({}) == "SUBMITTED"
