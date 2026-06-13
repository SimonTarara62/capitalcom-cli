"""Unit tests for the Capital.com HTTP client (offline)."""

from capital_cli import __version__
from capital_cli.core.http_client import CapitalClient


def test_client_sends_user_agent():
    client = CapitalClient()
    http = client._get_client()
    ua = http.headers.get("User-Agent", "")
    assert "capitalcom-cli" in ua
    assert __version__ in ua
    assert "github.com/SimonTarara62/capitalcom-cli" in ua
