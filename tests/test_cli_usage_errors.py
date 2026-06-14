import json
import subprocess
import sys


def _run(*args):
    return subprocess.run(
        [sys.executable, "-m", "capital_cli", *args], capture_output=True, text=True
    )


def test_missing_arg_json_is_structured():
    # preview-position requires EPIC/DIRECTION/SIZE; omit them
    proc = _run("--json", "trade", "preview-position")
    assert proc.returncode == 2, proc.stderr
    payload = json.loads(proc.stderr.strip().splitlines()[-1])
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_REQUEST"


def test_unknown_command_json_is_structured():
    proc = _run("--json", "bogus-command")
    assert proc.returncode == 2
    json.loads(proc.stderr.strip().splitlines()[-1])  # must parse
