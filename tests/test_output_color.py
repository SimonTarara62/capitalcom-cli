"""Color-policy resolution and wiring."""

from capital_cli.cli.output import Output, resolve_no_color


def test_no_color_env_disables(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    assert resolve_no_color(False) is True


def test_capctl_no_color_env_disables(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("CAPCTL_NO_COLOR", "1")
    assert resolve_no_color(False) is True


def test_term_dumb_disables(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("CAPCTL_NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "dumb")
    assert resolve_no_color(False) is True


def test_flag_disables(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("CAPCTL_NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    assert resolve_no_color(True) is True


def test_default_keeps_color(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("CAPCTL_NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    assert resolve_no_color(False) is False


def test_console_no_color_applied(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    out = Output()
    assert out.no_color is True
    assert out.console.no_color is True
    assert out.err.no_color is True
