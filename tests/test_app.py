from typer.testing import CliRunner

from capital_cli import __version__
from capital_cli.cli.app import app

runner = CliRunner()


def _all_output(result) -> str:
    """stdout plus stderr (click>=8.2 routes usage errors to stderr)."""
    combined = result.output
    try:
        combined += result.stderr
    except (ValueError, AttributeError):
        pass
    return combined


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_help_lists_command_groups():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for group in ["session", "market", "account", "trade", "watchlist", "stream"]:
        assert group in result.stdout


def test_demo_and_live_conflict():
    result = runner.invoke(app, ["--demo", "--live", "session", "status"])
    assert result.exit_code != 0
    text = _all_output(result).lower()
    assert "demo" in text or "live" in text
