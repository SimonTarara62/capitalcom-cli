import asyncio


def test_public_imports():
    from capital_cli.sdk import CapitalComApp, CapitalComConfig, RiskPolicy  # noqa: F401


def test_risk_policy_snapshot(monkeypatch):
    monkeypatch.setenv("CAP_ENV", "demo")
    monkeypatch.setenv("CAP_API_KEY", "k")
    monkeypatch.setenv("CAP_IDENTIFIER", "id@example.com")
    monkeypatch.setenv("CAP_API_PASSWORD", "pw")
    monkeypatch.setenv("CAP_MAX_POSITION_SIZE", "2.5")
    from capital_cli.core.config import reset_config
    reset_config()
    from capital_cli.sdk import CapitalComConfig, RiskPolicy
    policy = RiskPolicy.from_config(CapitalComConfig.from_env())
    assert policy.max_position_size == 2.5
    assert policy.allow_trading in (True, False)
    assert isinstance(policy.allowed_epics, list)


def test_app_exposes_services(monkeypatch):
    monkeypatch.setenv("CAP_ENV", "demo")
    monkeypatch.setenv("CAP_API_KEY", "k")
    monkeypatch.setenv("CAP_IDENTIFIER", "id@example.com")
    monkeypatch.setenv("CAP_API_PASSWORD", "pw")
    from capital_cli.core.config import reset_config
    reset_config()
    from capital_cli.sdk import CapitalComApp
    app = CapitalComApp()
    assert app.markets and app.accounts and app.watchlists and app.trading and app.stream
    assert app.session is not None
    assert app.risk_policy.max_position_size is not None


def _reset_all_singletons():
    from capital_cli.core.config import reset_config
    from capital_cli.core.http_client import reset_client
    from capital_cli.core.rate_limit import reset_rate_limiter
    from capital_cli.core.risk import reset_risk_engine
    from capital_cli.core.session import reset_session_manager
    from capital_cli.core.state import reset_state_store

    reset_config()
    reset_client()
    reset_session_manager()
    reset_risk_engine()
    reset_rate_limiter()
    reset_state_store()


def test_custom_config_is_honored_and_consistent(monkeypatch):
    # baseline env so from_env()/get_config() construct
    monkeypatch.setenv("CAP_ENV", "demo")
    monkeypatch.setenv("CAP_API_KEY", "k")
    monkeypatch.setenv("CAP_IDENTIFIER", "id@example.com")
    monkeypatch.setenv("CAP_API_PASSWORD", "pw")
    monkeypatch.setenv("CAP_MAX_POSITION_SIZE", "2.5")
    from capital_cli.core.config import get_config, reset_config
    reset_config()
    from capital_cli.sdk import CapitalComApp, CapitalComConfig
    custom = CapitalComConfig.from_env()
    object_max = 7.0
    # build a custom config instance with a different limit
    data = custom.model_dump()
    data["cap_max_position_size"] = object_max
    custom2 = CapitalComConfig.model_validate(data)
    try:
        app = CapitalComApp(config=custom2)
        # risk_policy reflects the passed config, not the old global
        assert app.risk_policy.max_position_size == object_max
        assert app.config.cap_max_position_size == object_max
        # and the global the services/risk read now reflects it too
        assert get_config().cap_max_position_size == object_max
    finally:
        # This test installs a custom global + rebuilds singletons; reset them
        # so subsequent tests rebuild from their own env (test isolation).
        _reset_all_singletons()


def test_aenter_logs_in_aexit_no_logout(monkeypatch):
    monkeypatch.setenv("CAP_ENV", "demo")
    monkeypatch.setenv("CAP_API_KEY", "k")
    monkeypatch.setenv("CAP_IDENTIFIER", "id@example.com")
    monkeypatch.setenv("CAP_API_PASSWORD", "pw")
    from capital_cli.core.config import reset_config
    reset_config()
    from capital_cli.sdk import CapitalComApp

    app = CapitalComApp()

    calls = {"login": 0, "logout": 0, "close": 0}

    async def fake_login():
        calls["login"] += 1

    async def fake_logout():
        calls["logout"] += 1

    monkeypatch.setattr(app.session, "ensure_logged_in", fake_login)
    monkeypatch.setattr(app.session, "logout", fake_logout)

    import capital_cli.core.http_client as hc

    class _FakeClient:
        async def close(self):
            calls["close"] += 1

    monkeypatch.setattr(hc, "get_client", lambda: _FakeClient())

    async def _run():
        async with app:
            pass

    asyncio.run(_run())
    assert calls["login"] == 1
    assert calls["logout"] == 0   # __aexit__ must NOT logout (preserve cached session #10)
    assert calls["close"] == 1
