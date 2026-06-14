"""The packaged metadata version must match capital_cli.__version__."""

import json
import subprocess
import sys
from importlib import metadata

import capital_cli


def test_metadata_matches_dunder_version() -> None:
    assert metadata.version("capitalcom-cli") == capital_cli.__version__


def test_version_json():
    proc = subprocess.run(
        [sys.executable, "-m", "capital_cli", "--json", "--version"], capture_output=True, text=True
    )
    payload = json.loads(proc.stdout.strip())
    assert payload["name"] == "capctl"
    assert payload["version"]  # non-empty
