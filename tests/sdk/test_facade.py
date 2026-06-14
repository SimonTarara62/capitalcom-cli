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
    policy = RiskPolicy(CapitalComConfig.from_env())
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
