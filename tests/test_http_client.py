"""Unit tests for the Capital.com HTTP client (offline)."""

import pytest

from capital_cli import __version__
from capital_cli.core.http_client import CapitalClient


def test_client_sends_user_agent():
    client = CapitalClient()
    http = client._get_client()
    ua = http.headers.get("User-Agent", "")
    assert "capitalcom-cli" in ua
    assert __version__ in ua
    assert "github.com/SimonTarara62/capitalcom-cli" in ua


async def test_get_relogins_once_on_401(monkeypatch):
    client = CapitalClient()
    calls = {"requests": 0, "relogin": 0}

    async def fake_relogin():
        calls["relogin"] += 1

    client.set_relogin(fake_relogin)

    class _Resp:
        def __init__(self, status):
            self.status_code = status
            self.reason_phrase = "x"
            self.text = "{}"

        def json(self):
            return {}

    async def fake_request(*a, **k):
        calls["requests"] += 1
        return _Resp(401 if calls["requests"] == 1 else 200)

    http = client._get_client()
    monkeypatch.setattr(http, "request", fake_request)

    async def _acquire(timeout=None):
        return True

    monkeypatch.setattr(client.rate_limiter, "acquire_global", _acquire)

    resp = await client.get("/positions")
    assert resp.status_code == 200
    assert calls["relogin"] == 1
    assert calls["requests"] == 2


async def test_get_without_relogin_raises_on_401(monkeypatch):
    from capital_cli.core.errors import SessionError

    client = CapitalClient()

    class _Resp:
        status_code = 401
        reason_phrase = "x"
        text = "{}"

        def json(self):
            return {}

    async def fake_request(*a, **k):
        return _Resp()

    http = client._get_client()
    monkeypatch.setattr(http, "request", fake_request)

    async def _acquire(timeout=None):
        return True

    monkeypatch.setattr(client.rate_limiter, "acquire_global", _acquire)

    with pytest.raises(SessionError):
        await client.get("/positions")
