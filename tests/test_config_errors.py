"""Missing credentials must surface as CONFIG_MISSING (exit 3), not a traceback."""

import json
import subprocess
import sys


def _run(*args, env_overrides):
    import os
    env = {**os.environ, "CAP_ENV_FILE": "/nonexistent-capctl.env", **env_overrides}
    # ensure no ambient creds leak in from the developer's shell
    for k in ("CAP_API_KEY", "CAP_IDENTIFIER", "CAP_API_PASSWORD"):
        env.pop(k, None)
    return subprocess.run(
        [sys.executable, "-m", "capital_cli", *args],
        capture_output=True, text=True, env=env,
    )


def test_missing_creds_exit_3_and_no_traceback():
    proc = _run("account", "list", env_overrides={})
    assert proc.returncode == 3, proc.stderr
    assert "Traceback" not in proc.stderr


def test_missing_creds_json_is_parseable():
    proc = _run("--json", "account", "list", env_overrides={})
    assert proc.returncode == 3
    payload = json.loads(proc.stderr.strip().splitlines()[-1])
    assert payload["ok"] is False
    assert payload["error"]["code"] == "CONFIG_MISSING"
