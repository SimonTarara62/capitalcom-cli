from capital_cli.services.confirmations import build_broker_request, mutation_status


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
