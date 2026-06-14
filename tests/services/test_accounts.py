"""Tests locking AccountService to the same broker requests the CLI made before.

Critical: the mutation guard (validate_mutation_guards / confirm checks) now lives
INSIDE the service and must run BEFORE any HTTP request.
"""

from __future__ import annotations

from typing import Any

import pytest

from capital_cli.core.errors import ConfirmRequiredError
from capital_cli.services.accounts import AccountService


class _FakeResp:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeClient:
    def __init__(self, payload: dict[str, Any] | None = None) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self._payload = payload if payload is not None else {"accounts": []}

    async def get(self, path: str, **kw: Any) -> _FakeResp:
        self.calls.append(("GET", path, kw))
        return _FakeResp(self._payload)

    async def put(self, path: str, **kw: Any) -> _FakeResp:
        self.calls.append(("PUT", path, kw))
        return _FakeResp(self._payload)

    async def post(self, path: str, **kw: Any) -> _FakeResp:
        self.calls.append(("POST", path, kw))
        return _FakeResp(self._payload)


class _FakeSession:
    def __init__(self) -> None:
        self.logged_in = 0
        self.account_id = "ACC1"

    async def ensure_logged_in(self) -> None:
        self.logged_in += 1


class _FakeRisk:
    def __init__(self, raises: Exception | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._raises = raises

    def validate_mutation_guards(self, *, confirm: bool) -> None:
        self.calls.append({"confirm": confirm})
        if self._raises is not None:
            raise self._raises


class _FakeConfig:
    def __init__(self, *, env: str = "demo", require_confirm: bool = True) -> None:
        self.cap_env = type("E", (), {"value": env})()
        self.cap_require_explicit_confirm = require_confirm


@pytest.fixture
def wired(monkeypatch):
    def _wire(
        payload: dict[str, Any] | None = None,
        *,
        risk: _FakeRisk | None = None,
        config: _FakeConfig | None = None,
    ):
        fake = _FakeClient(payload)
        session = _FakeSession()
        risk = risk if risk is not None else _FakeRisk()
        config = config if config is not None else _FakeConfig()
        monkeypatch.setattr("capital_cli.services.accounts.get_client", lambda: fake)
        monkeypatch.setattr(
            "capital_cli.services.accounts.get_session_manager", lambda: session
        )
        monkeypatch.setattr("capital_cli.services.accounts.get_risk_engine", lambda: risk)
        monkeypatch.setattr("capital_cli.services.accounts.get_config", lambda: config)
        return fake, session, risk, config

    return _wire


async def test_list_hits_accounts_endpoint(wired):
    fake, session, _, _ = wired({"accounts": [{"accountId": "ACC1"}]})
    out = await AccountService().list()
    assert session.logged_in == 1
    assert fake.calls[0][0] == "GET"
    assert fake.calls[0][1] == "/accounts"
    assert out["accounts"] == [{"accountId": "ACC1"}]
    assert out["active_account_id"] == "ACC1"


async def test_get_preferences_hits_endpoint(wired):
    fake, session, _, _ = wired({"hedgingMode": False})
    out = await AccountService().get_preferences()
    assert session.logged_in == 1
    assert fake.calls[0][0] == "GET"
    assert fake.calls[0][1] == "/accounts/preferences"
    assert out == {"hedgingMode": False}


async def test_set_preferences_calls_mutation_guard_before_put(wired):
    risk = _FakeRisk()
    fake, _, _, _ = wired({"status": "SUCCESS"}, risk=risk)
    out = await AccountService().set_preferences(
        leverages={"SHARES": 5}, confirm=True
    )
    # Guard ran with confirm=True
    assert risk.calls == [{"confirm": True}]
    # PUT issued with the same body the CLI built
    assert fake.calls[0][0] == "PUT"
    assert fake.calls[0][1] == "/accounts/preferences"
    assert fake.calls[0][2]["json"] == {"leverages": {"SHARES": 5}}
    assert out == {"status": "SUCCESS"}


async def test_set_preferences_body_hedging_and_leverage(wired):
    fake, _, _, _ = wired({"status": "SUCCESS"})
    await AccountService().set_preferences(
        hedging=False, leverages={"SHARES": 5}, confirm=True
    )
    assert fake.calls[0][2]["json"] == {
        "hedgingMode": False,
        "leverages": {"SHARES": 5},
    }


async def test_set_preferences_guard_raises_blocks_put(wired):
    risk = _FakeRisk(raises=ConfirmRequiredError())
    fake, _, _, _ = wired(risk=risk)
    with pytest.raises(ConfirmRequiredError):
        await AccountService().set_preferences(leverages={"SHARES": 5}, confirm=False)
    # Guard ran, but NO HTTP request was made.
    assert risk.calls == [{"confirm": False}]
    assert fake.calls == []


async def test_demo_topup_guards_before_post(wired):
    fake, _, _, _ = wired({"status": "SUCCESS"})
    out = await AccountService().demo_topup(500.0, confirm=True)
    assert fake.calls[0][0] == "POST"
    assert fake.calls[0][1] == "/accounts/topUp"
    assert fake.calls[0][2]["json"] == {"amount": 500.0}
    assert out == {"status": "SUCCESS"}


async def test_demo_topup_requires_confirm_blocks_post(wired):
    fake, _, _, _ = wired(config=_FakeConfig(require_confirm=True))
    with pytest.raises(ConfirmRequiredError):
        await AccountService().demo_topup(500.0, confirm=False)
    # No HTTP request was made.
    assert fake.calls == []


async def test_demo_topup_rejects_non_demo_env(wired):
    fake, _, _, _ = wired(config=_FakeConfig(env="live"))
    with pytest.raises(ValueError):
        await AccountService().demo_topup(500.0, confirm=True)
    assert fake.calls == []


async def test_history_activity_endpoint_and_params(wired):
    fake, _, _, _ = wired({"activities": []})
    await AccountService().history_activity(
        last_period=3600,
        from_date="2024-01-01",
        to_date="2024-01-02",
        detailed=True,
        deal_id="D9",
    )
    assert fake.calls[0][0] == "GET"
    assert fake.calls[0][1] == "/history/activity"
    assert fake.calls[0][2]["params"] == {
        "lastPeriod": 3600,
        "from": "2024-01-01",
        "to": "2024-01-02",
        "detailed": "true",
        "dealId": "D9",
    }


async def test_history_activity_minimal_params(wired):
    fake, _, _, _ = wired({"activities": []})
    await AccountService().history_activity(last_period=600)
    assert fake.calls[0][2]["params"] == {"lastPeriod": 600}


async def test_history_transactions_endpoint_and_params(wired):
    fake, _, _, _ = wired({"transactions": []})
    await AccountService().history_transactions(
        last_period=600, type_="DEPOSIT", from_date="2024-01-01", to_date="2024-01-02"
    )
    assert fake.calls[0][0] == "GET"
    assert fake.calls[0][1] == "/history/transactions"
    assert fake.calls[0][2]["params"] == {
        "lastPeriod": 600,
        "type": "DEPOSIT",
        "from": "2024-01-01",
        "to": "2024-01-02",
    }


async def test_history_transactions_minimal_params(wired):
    fake, _, _, _ = wired({"transactions": []})
    await AccountService().history_transactions(last_period=600)
    assert fake.calls[0][2]["params"] == {"lastPeriod": 600}
