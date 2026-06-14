"""Tests locking TradingService to the same broker orchestration trade_cmds did.

Critical invariants (MOVE-NOT-REWRITE):
- Execution guards run INSIDE the service BEFORE any mutating HTTP call.
- execute-position fetches open positions and runs check_open_position_limit.
- Each mutation: guard -> [limit] -> preview -> build -> HTTP -> increment ->
  confirm -> audit, with identical kwargs. A blocked guard makes NO HTTP call,
  NO increment, and NO audit.
- audit_mutation now lives in the service module (SDK consumers get auditing).
"""

from __future__ import annotations

from typing import Any

import pytest

from capital_cli.core.errors import ConfirmRequiredError, RiskLimitError
from capital_cli.services.trading import TradingService


class _FakeResp:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeClient:
    def __init__(self, responses: dict[str, dict[str, Any]] | None = None) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self._responses = responses or {}

    def _resp(self, path: str) -> _FakeResp:
        return _FakeResp(self._responses.get(path, {}))

    async def get(self, path: str, **kw: Any) -> _FakeResp:
        self.calls.append(("GET", path, kw))
        return self._resp(path)

    async def post(self, path: str, **kw: Any) -> _FakeResp:
        self.calls.append(("POST", path, kw))
        return self._resp(path)

    async def delete(self, path: str, **kw: Any) -> _FakeResp:
        self.calls.append(("DELETE", path, kw))
        return self._resp(path)

    async def put(self, path: str, **kw: Any) -> _FakeResp:
        self.calls.append(("PUT", path, kw))
        return self._resp(path)


class _FakeSession:
    def __init__(self) -> None:
        self.logged_in = 0
        self.account_id = "ACC1"

    async def ensure_logged_in(self) -> None:
        self.logged_in += 1


class _FakePreview:
    def __init__(self, normalized: dict[str, Any]) -> None:
        self.normalized_request = normalized


class _FakeRisk:
    def __init__(
        self,
        *,
        normalized: dict[str, Any] | None = None,
        guard_raises: Exception | None = None,
        limit_raises: Exception | None = None,
    ) -> None:
        self.guard_calls: list[dict[str, Any]] = []
        self.limit_calls: list[int] = []
        self.increment_calls = 0
        self._normalized = normalized or {"epic": "GOLD", "direction": "BUY", "size": 1.0}
        self._guard_raises = guard_raises
        self._limit_raises = limit_raises

    def validate_execution_guards(self, *, confirm: bool, preview_id: str | None = None) -> None:
        self.guard_calls.append({"confirm": confirm, "preview_id": preview_id})
        if self._guard_raises is not None:
            raise self._guard_raises

    def check_open_position_limit(self, count: int) -> None:
        self.limit_calls.append(count)
        if self._limit_raises is not None:
            raise self._limit_raises

    def get_preview(self, preview_id: str) -> _FakePreview:
        return _FakePreview(self._normalized)

    def increment_order_count(self) -> None:
        self.increment_calls += 1


class _FakeConfig:
    def __init__(self, env: str = "demo") -> None:
        self.cap_env = type("E", (), {"value": env})()


@pytest.fixture
def wired(monkeypatch):
    audited: list[dict[str, Any]] = []
    confirmed: list[tuple[str, float]] = []

    def _wire(
        *,
        responses: dict[str, dict[str, Any]] | None = None,
        risk: _FakeRisk | None = None,
        confirmation: dict[str, Any] | None = None,
    ):
        client = _FakeClient(responses)
        session = _FakeSession()
        risk = risk if risk is not None else _FakeRisk()
        config = _FakeConfig()

        async def fake_wait(deal_reference: str, timeout_s: float, **kw: Any) -> dict[str, Any]:
            confirmed.append((deal_reference, timeout_s))
            return confirmation if confirmation is not None else {"status": "ACCEPTED"}

        def fake_audit(**kwargs: Any) -> None:
            audited.append(kwargs)

        monkeypatch.setattr("capital_cli.services.trading.get_client", lambda: client)
        monkeypatch.setattr("capital_cli.services.trading.get_session_manager", lambda: session)
        monkeypatch.setattr("capital_cli.services.trading.get_risk_engine", lambda: risk)
        monkeypatch.setattr("capital_cli.services.trading.get_config", lambda: config)
        monkeypatch.setattr("capital_cli.services.trading.wait_for_confirmation", fake_wait)
        monkeypatch.setattr("capital_cli.services.trading.audit_mutation", fake_audit)
        return client, session, risk

    return _wire, audited, confirmed


# ----- Reads -----


async def test_list_positions_limit(wired):
    wire, _, _ = wired
    client, session, _ = wire(
        responses={"/positions": {"positions": [{"i": i} for i in range(5)]}}
    )
    out = await TradingService().list_positions(limit=2)
    assert session.logged_in == 1
    assert client.calls[0] == ("GET", "/positions", {})
    assert out["positions"] == [{"i": 0}, {"i": 1}]


async def test_list_positions_no_limit(wired):
    wire, _, _ = wired
    client, _, _ = wire(
        responses={"/positions": {"positions": [{"i": i} for i in range(5)]}}
    )
    out = await TradingService().list_positions()
    assert len(out["positions"]) == 5


async def test_get_position(wired):
    wire, _, _ = wired
    client, _, _ = wire(responses={"/positions/D1": {"position": {"dealId": "D1"}}})
    out = await TradingService().get_position("D1")
    assert client.calls[0] == ("GET", "/positions/D1", {})
    assert out["position"]["dealId"] == "D1"


async def test_list_orders_limit(wired):
    wire, _, _ = wired
    client, _, _ = wire(
        responses={"/workingorders": {"workingOrders": [{"i": i} for i in range(5)]}}
    )
    out = await TradingService().list_orders(limit=3)
    assert client.calls[0] == ("GET", "/workingorders", {})
    assert out["workingOrders"] == [{"i": 0}, {"i": 1}, {"i": 2}]


# ----- execute-position -----


async def test_execute_position_blocked_without_confirm(wired):
    wire, audited, confirmed = wired
    risk = _FakeRisk(guard_raises=ConfirmRequiredError())
    client, _, _ = wire(risk=risk)
    with pytest.raises(ConfirmRequiredError):
        await TradingService().execute_position("PV1", confirm=False)
    # Guard ran with confirm=False, but NO HTTP, NO increment, NO audit.
    assert risk.guard_calls == [{"confirm": False, "preview_id": "PV1"}]
    assert client.calls == []
    assert risk.increment_calls == 0
    assert audited == []


async def test_execute_position_blocked_at_open_limit(wired):
    wire, audited, _ = wired
    risk = _FakeRisk(limit_raises=RiskLimitError("limit reached"))
    client, _, _ = wire(
        risk=risk, responses={"/positions": {"positions": [{"position": {}}]}}
    )
    with pytest.raises(RiskLimitError):
        await TradingService().execute_position("PV1", confirm=True)
    # Open positions were fetched and the limit was checked; no POST/increment/audit.
    assert client.calls == [("GET", "/positions", {})]
    assert risk.limit_calls == [1]
    assert risk.increment_calls == 0
    assert audited == []


async def test_execute_position_happy_path(wired):
    wire, audited, confirmed = wired
    risk = _FakeRisk(normalized={"epic": "GOLD", "direction": "BUY", "size": 1.0})
    # Both GET /positions (open-position count source) and POST /positions share
    # this payload: it has no "positions" key (count 0) and carries dealReference
    # for the POST response.
    client, _, _ = wire(risk=risk, responses={"/positions": {"dealReference": "o_x"}})
    out = await TradingService().execute_position("PV1", confirm=True, timeout_s=30.0)

    # Sequence: guard -> open-positions fetch -> limit -> preview -> POST
    assert risk.guard_calls == [{"confirm": True, "preview_id": "PV1"}]
    assert risk.limit_calls == [0]  # empty positions list from {"dealReference"...}
    assert client.calls[0] == ("GET", "/positions", {})
    post = client.calls[1]
    assert post[0] == "POST"
    assert post[1] == "/positions"
    assert post[2]["json"] == {"epic": "GOLD", "direction": "BUY", "size": 1.0}
    assert post[2]["rate_limit_type"] == "trading"
    assert risk.increment_calls == 1
    assert confirmed == [("o_x", 30.0)]
    assert out["confirmation"] == {"status": "ACCEPTED"}
    assert out["active_account_id"] == "ACC1"
    assert audited[0]["command"] == "execute-position"
    assert audited[0]["preview_id"] == "PV1"
    assert audited[0]["deal_reference"] == "o_x"
    assert audited[0]["status"] == "ACCEPTED"
    assert audited[0]["epic"] == "GOLD"
    assert audited[0]["size"] == 1.0


async def test_execute_position_no_wait_skips_confirmation(wired):
    wire, audited, confirmed = wired
    risk = _FakeRisk()
    client, _, _ = wire(risk=risk, responses={"/positions": {"dealReference": "o_x"}})
    out = await TradingService().execute_position("PV1", confirm=True, wait=False)
    assert confirmed == []
    assert "confirmation" not in out
    # Audit still happens with SUBMITTED status.
    assert audited[0]["status"] == "SUBMITTED"


# ----- execute-order -----


async def test_execute_working_order_happy_path(wired):
    wire, audited, confirmed = wired
    risk = _FakeRisk(
        normalized={
            "epic": "GOLD",
            "direction": "BUY",
            "size": 1.0,
            "type": "LIMIT",
            "level": 1900.0,
        }
    )
    client, _, _ = wire(risk=risk, responses={"/workingorders": {"dealReference": "o_y"}})
    await TradingService().execute_working_order("PV2", confirm=True)
    # No open-position limit check for working orders.
    assert risk.limit_calls == []
    post = client.calls[0]
    assert post[0] == "POST"
    assert post[1] == "/workingorders"
    assert post[2]["rate_limit_type"] == "trading"
    assert post[2]["json"]["type"] == "LIMIT"
    assert post[2]["json"]["level"] == 1900.0
    assert risk.increment_calls == 1
    assert audited[0]["command"] == "execute-order"
    assert audited[0]["deal_reference"] == "o_y"


async def test_execute_working_order_blocked_without_confirm(wired):
    wire, audited, _ = wired
    risk = _FakeRisk(guard_raises=ConfirmRequiredError())
    client, _, _ = wire(risk=risk)
    with pytest.raises(ConfirmRequiredError):
        await TradingService().execute_working_order("PV2", confirm=False)
    assert client.calls == []
    assert risk.increment_calls == 0
    assert audited == []


# ----- close -----


async def test_close_position_happy_path(wired):
    wire, audited, confirmed = wired
    risk = _FakeRisk()
    client, _, _ = wire(risk=risk, responses={"/positions/D1": {"dealReference": "o_c"}})
    out = await TradingService().close_position("D1", confirm=True, timeout_s=20.0)
    assert risk.guard_calls == [{"confirm": True, "preview_id": None}]
    assert client.calls[0] == ("DELETE", "/positions/D1", {})
    assert confirmed == [("o_c", 20.0)]
    assert out["active_account_id"] == "ACC1"
    assert audited[0]["command"] == "close"
    assert audited[0]["deal_reference"] == "o_c"


async def test_close_position_blocked_without_confirm(wired):
    wire, audited, _ = wired
    risk = _FakeRisk(guard_raises=ConfirmRequiredError())
    client, _, _ = wire(risk=risk)
    with pytest.raises(ConfirmRequiredError):
        await TradingService().close_position("D1", confirm=False)
    assert client.calls == []
    assert audited == []


# ----- cancel -----


async def test_cancel_order_happy_path(wired):
    wire, audited, confirmed = wired
    risk = _FakeRisk()
    client, _, _ = wire(risk=risk, responses={"/workingorders/D2": {"dealReference": "o_z"}})
    await TradingService().cancel_order("D2", confirm=True)
    assert client.calls[0] == ("DELETE", "/workingorders/D2", {})
    assert audited[0]["command"] == "cancel"
    assert audited[0]["deal_reference"] == "o_z"


async def test_cancel_order_blocked_without_confirm(wired):
    wire, audited, _ = wired
    risk = _FakeRisk(guard_raises=ConfirmRequiredError())
    client, _, _ = wire(risk=risk)
    with pytest.raises(ConfirmRequiredError):
        await TradingService().cancel_order("D2", confirm=False)
    assert client.calls == []
    assert audited == []


# ----- amend -----


async def test_amend_position_happy_path(wired):
    wire, audited, _ = wired
    risk = _FakeRisk()
    client, _, _ = wire(risk=risk, responses={"/positions/D1": {"dealReference": "o_a"}})
    await TradingService().amend_position("D1", body={"stopLevel": 100.0}, confirm=True)
    put = client.calls[0]
    assert put[0] == "PUT"
    assert put[1] == "/positions/D1"
    assert put[2]["json"] == {"stopLevel": 100.0}
    assert audited[0]["command"] == "amend-position"


async def test_amend_order_happy_path(wired):
    wire, audited, _ = wired
    risk = _FakeRisk()
    client, _, _ = wire(risk=risk, responses={"/workingorders/D2": {"dealReference": "o_b"}})
    await TradingService().amend_order("D2", body={"level": 2300.0}, confirm=True)
    put = client.calls[0]
    assert put[0] == "PUT"
    assert put[1] == "/workingorders/D2"
    assert put[2]["json"] == {"level": 2300.0}
    assert audited[0]["command"] == "amend-order"


async def test_amend_position_blocked_without_confirm(wired):
    wire, audited, _ = wired
    risk = _FakeRisk(guard_raises=ConfirmRequiredError())
    client, _, _ = wire(risk=risk)
    with pytest.raises(ConfirmRequiredError):
        await TradingService().amend_position("D1", body={"stopLevel": 100.0}, confirm=False)
    assert client.calls == []
    assert audited == []
