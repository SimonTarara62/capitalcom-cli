"""The packaged metadata version must match capital_cli.__version__."""

from importlib import metadata

import capital_cli


def test_metadata_matches_dunder_version() -> None:
    assert metadata.version("capitalcom-cli") == capital_cli.__version__
