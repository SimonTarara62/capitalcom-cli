"""Expected errors must carry an actionable, CLI-phrased remediation hint."""

from capital_cli.core.errors import (
    ConfirmRequiredError,
    DryRunError,
    EpicNotAllowedError,
)


def test_confirm_required_points_at_yes_flag():
    assert "--yes" in ConfirmRequiredError().message


def test_dry_run_points_at_env_var():
    msg = DryRunError().message
    assert "CAP_DRY_RUN" in msg


def test_epic_not_allowed_points_at_allowlist():
    err = EpicNotAllowedError("GOLD", [])
    assert "CAP_ALLOWED_EPICS" in err.message
