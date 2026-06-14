"""Issue #10: session tokens persist across invocations via the state file."""

from datetime import datetime, timedelta, timezone

from capital_cli.core import session as session_mod
from capital_cli.core.state import StateStore


def _store(tmp_path):
    return StateStore(path=tmp_path / "state.json")


def test_save_load_clear_roundtrip(tmp_path):
    store = _store(tmp_path)
    now = datetime.now(timezone.utc).isoformat()
    store.save_session(env="demo", cst="CST1", x_security_token="XST1", last_used_at=now, account_id="ACC1")
    got = store.load_session("demo")
    assert got is not None
    assert got["cst"] == "CST1"
    assert got["x_security_token"] == "XST1"
    assert got["account_id"] == "ACC1"
    store.clear_session()
    assert store.load_session("demo") is None


def test_load_is_env_scoped(tmp_path):
    store = _store(tmp_path)
    now = datetime.now(timezone.utc).isoformat()
    store.save_session(env="demo", cst="C", x_security_token="X", last_used_at=now, account_id=None)
    assert store.load_session("live") is None
    assert store.load_session("demo") is not None


def test_file_is_chmod_600(tmp_path):
    store = _store(tmp_path)
    now = datetime.now(timezone.utc).isoformat()
    store.save_session(env="demo", cst="C", x_security_token="X", last_used_at=now, account_id=None)
    mode = (tmp_path / "state.json").stat().st_mode & 0o777
    assert mode == 0o600


def _reset_singletons():
    from capital_cli.core.config import reset_config
    from capital_cli.core.http_client import reset_client
    from capital_cli.core.state import reset_state_store

    reset_config()
    reset_client()
    reset_state_store()
    session_mod.reset_session_manager()


def test_session_manager_restores_cached_tokens(tmp_path, monkeypatch):
    monkeypatch.setenv("CAPCTL_STATE_FILE", str(tmp_path / "state.json"))
    monkeypatch.setenv("CAP_PERSIST_SESSION", "true")
    monkeypatch.setenv("CAP_ENV", "demo")
    monkeypatch.setenv("CAP_API_KEY", "k")
    monkeypatch.setenv("CAP_IDENTIFIER", "id@example.com")
    monkeypatch.setenv("CAP_API_PASSWORD", "pw")
    _reset_singletons()
    from capital_cli.core.state import get_state_store
    now = datetime.now(timezone.utc).isoformat()
    get_state_store().save_session(env="demo", cst="CST1", x_security_token="XST1", last_used_at=now, account_id="ACC1")
    sm = session_mod.get_session_manager()
    assert sm.tokens is not None
    assert sm.tokens.cst == "CST1"
    assert sm.account_id == "ACC1"
    assert sm.tokens.is_expired() is False


def test_expired_cached_session_is_ignored_and_cleared(tmp_path, monkeypatch):
    monkeypatch.setenv("CAPCTL_STATE_FILE", str(tmp_path / "state.json"))
    monkeypatch.setenv("CAP_PERSIST_SESSION", "true")
    monkeypatch.setenv("CAP_ENV", "demo")
    monkeypatch.setenv("CAP_API_KEY", "k")
    monkeypatch.setenv("CAP_IDENTIFIER", "id@example.com")
    monkeypatch.setenv("CAP_API_PASSWORD", "pw")
    _reset_singletons()
    from capital_cli.core.state import get_state_store
    stale = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
    get_state_store().save_session(env="demo", cst="OLD", x_security_token="OLD", last_used_at=stale, account_id="ACC1")
    sm = session_mod.get_session_manager()
    assert sm.tokens is None
    assert get_state_store().load_session("demo") is None
