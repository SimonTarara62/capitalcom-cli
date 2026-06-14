"""Tests locking WatchlistService to the same broker requests the CLI made before.

Critical: the mutation guard (validate_mutation_guards / confirm checks) now lives
INSIDE the service and must run BEFORE any HTTP request.
"""

from __future__ import annotations

from typing import Any

import pytest

from capital_cli.core.errors import ConfirmRequiredError
from capital_cli.services.watchlists import WatchlistService


class _FakeResp:
    def __init__(self, payload: dict[str, Any], *, text: str = "{}") -> None:
        self._payload = payload
        self.text = text

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeClient:
    def __init__(self, payload: dict[str, Any] | None = None, *, text: str = "{}") -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self._payload = payload if payload is not None else {"watchlists": []}
        self._text = text

    async def get(self, path: str, **kw: Any) -> _FakeResp:
        self.calls.append(("GET", path, kw))
        return _FakeResp(self._payload, text=self._text)

    async def post(self, path: str, **kw: Any) -> _FakeResp:
        self.calls.append(("POST", path, kw))
        return _FakeResp(self._payload, text=self._text)

    async def put(self, path: str, **kw: Any) -> _FakeResp:
        self.calls.append(("PUT", path, kw))
        return _FakeResp(self._payload, text=self._text)

    async def delete(self, path: str, **kw: Any) -> _FakeResp:
        self.calls.append(("DELETE", path, kw))
        return _FakeResp(self._payload, text=self._text)


class _FakeSession:
    def __init__(self) -> None:
        self.logged_in = 0

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


@pytest.fixture
def wired(monkeypatch):
    def _wire(
        payload: dict[str, Any] | None = None,
        *,
        risk: _FakeRisk | None = None,
        text: str = "{}",
    ):
        fake = _FakeClient(payload, text=text)
        session = _FakeSession()
        risk = risk if risk is not None else _FakeRisk()
        monkeypatch.setattr("capital_cli.services.watchlists.get_client", lambda: fake)
        monkeypatch.setattr(
            "capital_cli.services.watchlists.get_session_manager", lambda: session
        )
        monkeypatch.setattr(
            "capital_cli.services.watchlists.get_risk_engine", lambda: risk
        )
        return fake, session, risk

    return _wire


# --- reads -----------------------------------------------------------------


async def test_list_hits_watchlists_endpoint(wired):
    fake, session, _ = wired({"watchlists": [{"id": "1", "name": "Metals"}]})
    out = await WatchlistService().list()
    assert session.logged_in == 1
    assert fake.calls[0][0] == "GET"
    assert fake.calls[0][1] == "/watchlists"
    assert out == {"watchlists": [{"id": "1", "name": "Metals"}]}


async def test_get_hits_watchlist_id_path(wired):
    fake, session, _ = wired({"markets": []})
    out = await WatchlistService().get("42")
    assert session.logged_in == 1
    assert fake.calls[0][0] == "GET"
    assert fake.calls[0][1] == "/watchlists/42"
    assert out == {"markets": []}


# --- create ----------------------------------------------------------------


async def test_create_guards_before_post(wired):
    risk = _FakeRisk()
    fake, _, _ = wired({"watchlistId": "9", "status": "SUCCESS"}, risk=risk)
    out = await WatchlistService().create("Crypto", confirm=True)
    assert risk.calls == [{"confirm": True}]
    assert fake.calls[0][0] == "POST"
    assert fake.calls[0][1] == "/watchlists"
    assert fake.calls[0][2]["json"] == {"name": "Crypto"}
    assert out == {"watchlistId": "9", "status": "SUCCESS"}


async def test_create_guard_raises_blocks_post(wired):
    risk = _FakeRisk(raises=ConfirmRequiredError())
    fake, _, _ = wired(risk=risk)
    with pytest.raises(ConfirmRequiredError):
        await WatchlistService().create("Crypto", confirm=False)
    assert risk.calls == [{"confirm": False}]
    assert fake.calls == []


# --- add_market ------------------------------------------------------------


async def test_add_market_guards_before_put(wired):
    risk = _FakeRisk()
    fake, _, _ = wired({"status": "SUCCESS"}, risk=risk)
    out = await WatchlistService().add_market("1", "GOLD", confirm=True)
    assert risk.calls == [{"confirm": True}]
    assert fake.calls[0][0] == "PUT"
    assert fake.calls[0][1] == "/watchlists/1"
    assert fake.calls[0][2]["json"] == {"epic": "GOLD"}
    assert out == {"status": "SUCCESS"}


async def test_add_market_guard_raises_blocks_put(wired):
    risk = _FakeRisk(raises=ConfirmRequiredError())
    fake, _, _ = wired(risk=risk)
    with pytest.raises(ConfirmRequiredError):
        await WatchlistService().add_market("1", "GOLD", confirm=False)
    assert risk.calls == [{"confirm": False}]
    assert fake.calls == []


# --- remove_market ---------------------------------------------------------


async def test_remove_market_guards_before_delete(wired):
    risk = _FakeRisk()
    fake, _, _ = wired({"status": "SUCCESS"}, risk=risk)
    out = await WatchlistService().remove_market("1", "GOLD", confirm=True)
    assert risk.calls == [{"confirm": True}]
    assert fake.calls[0][0] == "DELETE"
    assert fake.calls[0][1] == "/watchlists/1/GOLD"
    assert out == {"status": "SUCCESS"}


async def test_remove_market_empty_body_returns_status(wired):
    fake, _, _ = wired({}, text="")
    out = await WatchlistService().remove_market("1", "GOLD", confirm=True)
    assert fake.calls[0][0] == "DELETE"
    assert fake.calls[0][1] == "/watchlists/1/GOLD"
    assert out == {"status": "removed"}


async def test_remove_market_guard_raises_blocks_delete(wired):
    risk = _FakeRisk(raises=ConfirmRequiredError())
    fake, _, _ = wired(risk=risk)
    with pytest.raises(ConfirmRequiredError):
        await WatchlistService().remove_market("1", "GOLD", confirm=False)
    assert risk.calls == [{"confirm": False}]
    assert fake.calls == []


# --- delete ----------------------------------------------------------------


async def test_delete_guards_before_delete(wired):
    risk = _FakeRisk()
    fake, _, _ = wired({"status": "SUCCESS"}, risk=risk)
    out = await WatchlistService().delete("1", confirm=True)
    assert risk.calls == [{"confirm": True}]
    assert fake.calls[0][0] == "DELETE"
    assert fake.calls[0][1] == "/watchlists/1"
    assert out == {"status": "SUCCESS"}


async def test_delete_empty_body_returns_status(wired):
    fake, _, _ = wired({}, text="")
    out = await WatchlistService().delete("1", confirm=True)
    assert fake.calls[0][0] == "DELETE"
    assert fake.calls[0][1] == "/watchlists/1"
    assert out == {"status": "deleted"}


async def test_delete_guard_raises_blocks_delete(wired):
    risk = _FakeRisk(raises=ConfirmRequiredError())
    fake, _, _ = wired(risk=risk)
    with pytest.raises(ConfirmRequiredError):
        await WatchlistService().delete("1", confirm=False)
    assert risk.calls == [{"confirm": False}]
    assert fake.calls == []
