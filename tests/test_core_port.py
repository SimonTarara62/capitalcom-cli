"""Verify the core package imports cleanly and config resolves env files."""

import importlib


def test_all_core_modules_import():
    for mod in [
        "capital_cli.core.errors",
        "capital_cli.core.models",
        "capital_cli.core.rate_limit",
        "capital_cli.core.utils",
        "capital_cli.core.http_client",
        "capital_cli.core.session",
        "capital_cli.core.risk",
        "capital_cli.core.websocket_client",
        "capital_cli.core.config",
    ]:
        importlib.import_module(mod)


def test_base_error_renamed():
    from capital_cli.core.errors import CapitalCLIError, ErrorCode

    err = CapitalCLIError(ErrorCode.INTERNAL_ERROR, "boom")
    assert err.code == ErrorCode.INTERNAL_ERROR
    assert err.message == "boom"


def test_config_reads_explicit_env_file(tmp_path, monkeypatch):
    from capital_cli.core import config as cfg_mod

    env = tmp_path / "creds.env"
    env.write_text(
        "CAP_ENV=demo\n"
        "CAP_API_KEY=k\n"
        "CAP_IDENTIFIER=me@example.com\n"
        "CAP_API_PASSWORD=p\n"
        "CAP_ALLOWED_EPICS=GOLD,SILVER\n"
    )
    monkeypatch.setenv("CAP_ENV_FILE", str(env))
    cfg_mod.reset_config()
    cfg = cfg_mod.get_config()

    assert cfg.cap_env.value == "demo"
    assert cfg.base_url == "https://demo-api-capital.backend-capital.com"
    assert cfg.api_base_url.endswith("/api/v1")
    assert cfg.is_epic_allowed("GOLD") is False  # trading disabled by default
    cfg_mod.reset_config()


def test_set_config_injection(monkeypatch, tmp_path):
    from capital_cli.core import config as cfg_mod

    env = tmp_path / "c.env"
    env.write_text("CAP_API_KEY=k\nCAP_IDENTIFIER=a@b.c\nCAP_API_PASSWORD=p\n")
    monkeypatch.setenv("CAP_ENV_FILE", str(env))
    cfg_mod.reset_config()
    built = cfg_mod.Config(_env_file=str(env))
    cfg_mod.set_config(built)
    assert cfg_mod.get_config() is built
    cfg_mod.reset_config()
