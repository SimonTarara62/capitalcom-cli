"""init_state must reset dependent singletons so global config changes take effect."""

from capital_cli.cli.context import init_state


def _set_creds(monkeypatch):
    monkeypatch.setenv("CAP_API_KEY", "k")
    monkeypatch.setenv("CAP_IDENTIFIER", "a@b.c")
    monkeypatch.setenv("CAP_API_PASSWORD", "p")
    monkeypatch.delenv("CAP_ENV_FILE", raising=False)


def test_switching_demo_to_live_changes_client_base_url(monkeypatch):
    _set_creds(monkeypatch)

    # First, initialize in demo and materialize the client singleton.
    init_state(
        json_mode=False,
        env_file=None,
        env="demo",
        account=None,
        verbose=False,
    )
    from capital_cli.core.http_client import get_client

    demo_client = get_client()
    assert "demo-api-capital" in demo_client.config.api_base_url

    # Switching to live must rebuild the client with the live base_url.
    init_state(
        json_mode=False,
        env_file=None,
        env="live",
        account=None,
        verbose=False,
    )
    live_client = get_client()
    assert "demo-api-capital" not in live_client.config.api_base_url
    assert live_client.config.api_base_url.startswith(
        "https://api-capital.backend-capital.com"
    )
    # A fresh instance, not the stale demo one.
    assert live_client is not demo_client
