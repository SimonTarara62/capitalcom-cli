"""Unit tests for the SessionManager read passthroughs (server_time / details /
encryption_key) that back both the CLI session commands and the SDK."""

import asyncio

import pytest


@pytest.fixture
def _demo_env(monkeypatch):
    monkeypatch.setenv("CAP_ENV", "demo")
    monkeypatch.setenv("CAP_API_KEY", "k")
    monkeypatch.setenv("CAP_IDENTIFIER", "id@example.com")
    monkeypatch.setenv("CAP_API_PASSWORD", "pw")
    from capital_cli.core.config import reset_config

    reset_config()
    yield
    from capital_cli.core.config import reset_config as _rc

    _rc()


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload
        self.text = "x"

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, payload):
        self._payload = payload
        self.path = None

    def set_relogin(self, *_a):
        pass

    async def get(self, path):
        self.path = path
        return _FakeResp(self._payload)


def _make_sm(payload):
    from capital_cli.core.session import SessionManager

    sm = SessionManager()
    sm.client = _FakeClient(payload)
    return sm


def test_server_time_hits_time_endpoint(_demo_env):
    sm = _make_sm({"serverTime": "2026-06-14T00:00:00"})
    out = asyncio.run(sm.server_time())
    assert sm.client.path == "/time"
    assert out == {"serverTime": "2026-06-14T00:00:00"}


def test_server_time_wraps_bare_value(_demo_env):
    sm = _make_sm(1700000000000)
    out = asyncio.run(sm.server_time())
    assert out == {"serverTime": 1700000000000}


def test_encryption_key_hits_endpoint(_demo_env):
    sm = _make_sm({"encryptionKey": "abc", "timeStamp": 1})
    out = asyncio.run(sm.encryption_key())
    assert sm.client.path == "/session/encryptionKey"
    assert out["encryptionKey"] == "abc"


def test_details_logs_in_then_hits_session(_demo_env, monkeypatch):
    sm = _make_sm({"clientId": "c", "accountId": "a"})

    async def _noop():
        return None

    monkeypatch.setattr(sm, "ensure_logged_in", _noop)
    out = asyncio.run(sm.details())
    assert sm.client.path == "/session"
    assert out["accountId"] == "a"
