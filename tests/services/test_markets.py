"""Tests locking MarketService to the same broker requests the CLI made before."""

from __future__ import annotations

from typing import Any

import pytest

from capital_cli.services.markets import MarketService


class _FakeResp:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeClient:
    def __init__(self, payload: dict[str, Any] | None = None) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._payload = payload if payload is not None else {"markets": [{"epic": "GOLD"}]}

    async def get(self, path: str, **kw: Any) -> _FakeResp:
        self.calls.append((path, kw))
        return _FakeResp(self._payload)


class _FakeSession:
    def __init__(self) -> None:
        self.logged_in = 0

    async def ensure_logged_in(self) -> None:
        self.logged_in += 1


@pytest.fixture
def wired(monkeypatch):
    def _wire(payload: dict[str, Any] | None = None):
        fake = _FakeClient(payload)
        session = _FakeSession()
        monkeypatch.setattr("capital_cli.services.markets.get_client", lambda: fake)
        monkeypatch.setattr("capital_cli.services.markets.get_session_manager", lambda: session)
        return fake, session

    return _wire


async def test_search_hits_markets_endpoint(wired):
    fake, session = wired()
    out = await MarketService().search("gold", limit=5)
    assert out == {"markets": [{"epic": "GOLD"}]}
    assert session.logged_in == 1
    assert fake.calls[0][0] == "/markets"
    assert fake.calls[0][1]["params"] == {"searchTerm": "gold"}


async def test_search_with_epics(wired):
    fake, _ = wired()
    await MarketService().search(None, epics="GOLD,SILVER", limit=50)
    assert fake.calls[0][1]["params"] == {"epics": "GOLD,SILVER"}


async def test_search_truncates_to_limit(wired):
    payload = {"markets": [{"epic": f"M{i}"} for i in range(10)]}
    fake, _ = wired(payload)
    out = await MarketService().search("x", limit=3)
    assert len(out["markets"]) == 3
    # truncation is client-side, not a query param
    assert "limit" not in fake.calls[0][1]["params"]


async def test_get_hits_epic_path(wired):
    fake, _ = wired()
    await MarketService().get("GOLD")
    assert fake.calls[0][0] == "/markets/GOLD"


async def test_prices_hits_prices_endpoint(wired):
    fake, _ = wired()
    await MarketService().prices(
        "GOLD", resolution="HOUR", max=10, from_date="2024-01-01", to_date="2024-01-02"
    )
    path, kw = fake.calls[0]
    assert path == "/prices/GOLD"
    assert kw["params"] == {
        "resolution": "HOUR",
        "max": 10,
        "from": "2024-01-01",
        "to": "2024-01-02",
    }


async def test_prices_omits_unset_dates(wired):
    fake, _ = wired()
    await MarketService().prices("GOLD", resolution="MINUTE_15", max=200)
    assert fake.calls[0][1]["params"] == {"resolution": "MINUTE_15", "max": 200}


async def test_sentiment_single(wired):
    fake, _ = wired()
    await MarketService().sentiment(["GOLD"])
    assert fake.calls[0][0] == "/clientsentiment/GOLD"
    assert "params" not in fake.calls[0][1]


async def test_sentiment_batch(wired):
    fake, _ = wired()
    await MarketService().sentiment(["GOLD", "SILVER"])
    assert fake.calls[0][0] == "/clientsentiment"
    assert fake.calls[0][1]["params"] == {"marketIds": "GOLD,SILVER"}


async def test_navigation_root(wired):
    fake, _ = wired()
    await MarketService().navigation_root()
    assert fake.calls[0][0] == "/marketnavigation"


async def test_navigation_node(wired):
    fake, _ = wired()
    await MarketService().navigation_node("hierarchy_v1.commodities", limit=10)
    assert fake.calls[0][0] == "/marketnavigation/hierarchy_v1.commodities"
    assert fake.calls[0][1]["params"] == {"limit": 10}


async def test_navigation_node_no_limit(wired):
    fake, _ = wired()
    await MarketService().navigation_node("node1")
    assert fake.calls[0][1]["params"] == {}
