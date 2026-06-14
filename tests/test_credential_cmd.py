"""CAP_*_CMD credential-exec helpers source secrets from a command at runtime.

Precedence (highest to lowest):
  1. explicit CAP_<FIELD> env var
  2. CAP_<FIELD>_CMD command output
  3. value from the .env file

The _CMD output beats .env because it is injected into the process environment
(an env var) before the Config (which reads the .env file) is constructed.
A failing/timing-out/empty command raises a clear ConfigError that never echoes
the command's stdout/stderr (so secrets cannot leak through the error path).
"""

import json
import subprocess
import sys

import pytest

from capital_cli.core.config import get_config, reset_config
from capital_cli.core.errors import CapitalCLIError, ErrorCode


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    # Isolate from the developer's shell + the repo .env: point at a nonexistent env file
    # and clear all credential / _CMD vars before each test.
    for k in (
        "CAP_API_KEY",
        "CAP_IDENTIFIER",
        "CAP_API_PASSWORD",
        "CAP_API_KEY_CMD",
        "CAP_IDENTIFIER_CMD",
        "CAP_API_PASSWORD_CMD",
    ):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("CAP_ENV_FILE", str(tmp_path / "nonexistent.env"))
    reset_config()
    yield
    reset_config()


@pytest.mark.skipif(
    sys.platform == "win32", reason="uses a POSIX shell command as the CAP_*_CMD helper"
)
def test_cmd_output_resolves_secret(monkeypatch):
    monkeypatch.setenv("CAP_API_KEY", "dummy-key")
    monkeypatch.setenv("CAP_IDENTIFIER", "dummy@example.com")
    monkeypatch.setenv("CAP_API_PASSWORD_CMD", "printf supersecret")
    cfg = get_config()
    assert cfg.cap_api_password == "supersecret"


@pytest.mark.skipif(
    sys.platform == "win32", reason="uses a POSIX shell command as the CAP_*_CMD helper"
)
def test_failing_cmd_raises_clear_config_error_without_echoing_secret(monkeypatch):
    monkeypatch.setenv("CAP_API_KEY", "dummy-key")
    monkeypatch.setenv("CAP_IDENTIFIER", "dummy@example.com")
    # Command prints a secret to stdout/stderr then exits non-zero.
    monkeypatch.setenv(
        "CAP_API_PASSWORD_CMD",
        'sh -c "echo supersecret; echo leaked-on-stderr 1>&2; exit 3"',
    )
    with pytest.raises(CapitalCLIError) as exc_info:
        get_config()
    err = exc_info.value
    assert err.code in (ErrorCode.CONFIG_INVALID, ErrorCode.CONFIG_MISSING)
    assert "supersecret" not in err.message
    assert "leaked-on-stderr" not in err.message
    assert "CAP_API_PASSWORD_CMD" in err.message


@pytest.mark.skipif(
    sys.platform == "win32", reason="uses a POSIX shell command as the CAP_*_CMD helper"
)
def test_empty_cmd_output_raises_config_error(monkeypatch):
    monkeypatch.setenv("CAP_API_KEY", "dummy-key")
    monkeypatch.setenv("CAP_IDENTIFIER", "dummy@example.com")
    monkeypatch.setenv("CAP_API_PASSWORD_CMD", "true")  # exits 0 with no output
    with pytest.raises(CapitalCLIError) as exc_info:
        get_config()
    assert exc_info.value.code in (ErrorCode.CONFIG_INVALID, ErrorCode.CONFIG_MISSING)


def test_explicit_env_var_takes_precedence_over_cmd(monkeypatch):
    monkeypatch.setenv("CAP_API_KEY", "dummy-key")
    monkeypatch.setenv("CAP_IDENTIFIER", "dummy@example.com")
    monkeypatch.setenv("CAP_API_PASSWORD", "explicit-value")
    monkeypatch.setenv("CAP_API_PASSWORD_CMD", "printf should-not-run")
    cfg = get_config()
    assert cfg.cap_api_password == "explicit-value"


@pytest.mark.skipif(
    sys.platform == "win32", reason="uses a POSIX shell command as the CAP_*_CMD helper"
)
def test_cmd_output_overrides_dotenv_value(monkeypatch, tmp_path):
    env_file = tmp_path / "creds.env"
    env_file.write_text(
        "CAP_API_KEY=dummy-key\nCAP_IDENTIFIER=dummy@example.com\nCAP_API_PASSWORD=from-dotenv\n"
    )
    monkeypatch.setenv("CAP_ENV_FILE", str(env_file))
    monkeypatch.setenv("CAP_API_PASSWORD_CMD", "printf from-cmd")
    cfg = get_config()
    assert cfg.cap_api_password == "from-cmd"


def test_dotenv_value_used_when_no_cmd_and_no_env(monkeypatch, tmp_path):
    env_file = tmp_path / "creds.env"
    env_file.write_text(
        "CAP_API_KEY=dummy-key\nCAP_IDENTIFIER=dummy@example.com\nCAP_API_PASSWORD=from-dotenv\n"
    )
    monkeypatch.setenv("CAP_ENV_FILE", str(env_file))
    cfg = get_config()
    assert cfg.cap_api_password == "from-dotenv"


@pytest.mark.skipif(
    sys.platform == "win32", reason="uses a POSIX shell command as the CAP_*_CMD helper"
)
def test_helper_does_not_inherit_earlier_resolved_secret(monkeypatch, tmp_path):
    """A later credential helper must NOT see an earlier-resolved CAP_* secret.

    Credential helpers are a weaker trust boundary (third-party op/vault/pass or a
    user script) and must never inherit unrelated secrets. CAP_API_KEY is resolved
    via its _CMD helper first; when the CAP_API_PASSWORD helper runs afterwards it
    must observe CAP_API_KEY as MISSING (not injected, not ambient).
    """
    seen_file = tmp_path / "seen_api_key"
    monkeypatch.setenv("CAP_IDENTIFIER", "dummy@example.com")
    # First helper resolves CAP_API_KEY.
    monkeypatch.setenv("CAP_API_KEY_CMD", "printf supersecret-key")
    # Second helper records whatever CAP_API_KEY it inherited from its environment.
    helper = (
        f"{sys.executable} -c "
        '"import os,pathlib;'
        f"pathlib.Path({str(seen_file)!r}).write_text("
        "os.environ.get('CAP_API_KEY','MISSING'));"
        "print('pw-value')\""
    )
    monkeypatch.setenv("CAP_API_PASSWORD_CMD", helper)
    cfg = get_config()
    assert cfg.cap_api_password == "pw-value"
    assert cfg.cap_api_key == "supersecret-key"
    assert seen_file.read_text() == "MISSING", (
        "password helper inherited the earlier-resolved CAP_API_KEY"
    )


@pytest.mark.skipif(
    sys.platform == "win32", reason="uses a POSIX shell command as the CAP_*_CMD helper"
)
def test_failing_cmd_maps_to_exit_3_via_cli():
    import os

    env = dict(os.environ)
    for k in ("CAP_API_KEY", "CAP_IDENTIFIER", "CAP_API_PASSWORD", "CAP_API_PASSWORD_CMD"):
        env.pop(k, None)
    env["CAP_ENV_FILE"] = "/nonexistent-capctl.env"
    env["CAP_API_KEY"] = "dummy-key"
    env["CAP_IDENTIFIER"] = "dummy@example.com"
    env["CAP_API_PASSWORD_CMD"] = 'sh -c "echo supersecret; exit 3"'
    proc = subprocess.run(
        [sys.executable, "-m", "capital_cli", "--json", "account", "list"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 3, proc.stderr
    assert "Traceback" not in proc.stderr
    assert "supersecret" not in proc.stderr
    payload = json.loads(proc.stderr.strip().splitlines()[-1])
    assert payload["ok"] is False
    assert payload["error"]["code"] in ("CONFIG_INVALID", "CONFIG_MISSING")
    assert "supersecret" not in payload["error"]["message"]
