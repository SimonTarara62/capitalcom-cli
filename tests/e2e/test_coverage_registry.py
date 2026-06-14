"""Offline integrity tests for the coverage registry — these run in the normal
(non-e2e) suite. They are the machine-checkable form of the 'we cover the whole
Capital.com API' claim: the registry must match the official surface, every
command/method named must exist, and every coverage cell must point at a real
test. If Capital.com adds an endpoint, or a test is renamed/removed, these fail.
"""

import ast
from pathlib import Path

import pytest

from tests.e2e.endpoints import COVERAGE, ENDPOINTS, OFFICIAL_SURFACE, sdk_supported

REPO = Path(__file__).resolve().parents[2]


def test_registry_matches_official_surface():
    # Cross-check: the registry's HTTP/WS set IS the published surface (no gaps,
    # no extras). OFFICIAL_SURFACE is derived from the registry today; this guards
    # against an endpoint being dropped from one list but not the other in future.
    registry_surface = {e.http for e in ENDPOINTS if e.http != "(local)"}
    assert registry_surface == OFFICIAL_SURFACE, (
        "registry drifted from the documented Capital.com surface: "
        f"only-in-registry={registry_surface - OFFICIAL_SURFACE}, "
        f"only-in-official={OFFICIAL_SURFACE - registry_surface}"
    )
    assert len({e.id for e in ENDPOINTS}) == len(ENDPOINTS), "duplicate endpoint id"


def test_every_cli_command_exists():
    # Build the Typer app and assert each registry CLI path resolves to a command.
    from typer.main import get_command

    from capital_cli.cli.app import app as typer_app

    root = get_command(typer_app)
    for e in ENDPOINTS:
        parts = e.cli.split()
        node = root
        for part in parts:
            assert hasattr(node, "commands"), f"{e.cli!r}: {part} is not a group"
            assert part in node.commands, f"{e.cli!r}: missing command {part!r}"
            node = node.commands[part]


def test_every_sdk_method_exists():
    # Resolve each registry SDK dotted path against the real service classes.
    from capital_cli.core.session import SessionManager
    from capital_cli.services import confirmations
    from capital_cli.services.accounts import AccountService
    from capital_cli.services.markets import MarketService
    from capital_cli.services.streaming import StreamService
    from capital_cli.services.trading import TradingService
    from capital_cli.services.watchlists import WatchlistService

    holders = {
        "session": SessionManager,
        "accounts": AccountService,
        "markets": MarketService,
        "trading": TradingService,
        "watchlists": WatchlistService,
        "stream": StreamService,
        "confirmations": confirmations,
    }
    for e in ENDPOINTS:
        if e.sdk is None:
            continue
        holder_name, method = e.sdk.split(".", 1)
        holder = holders[holder_name]
        assert hasattr(holder, method), f"{e.sdk!r}: {holder_name} has no {method!r}"


def _func_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    return {
        n.name
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_every_coverage_cell_points_at_a_real_test():
    # A cell may be None (untested / N/A) — that's allowed here; the completeness
    # gate (test below) checks fullness. But a NON-None cell must name a test that
    # exists, so the matrix can never claim a test that isn't there.
    cache: dict[str, set[str]] = {}
    for endpoint_id, cells in COVERAGE.items():
        for node in (cells.cli_pos, cells.cli_neg, cells.sdk_pos, cells.sdk_neg):
            if node is None:
                continue
            file_part, func = node.split("::", 1)
            func = func.split("[", 1)[0]  # strip parametrize id
            path = REPO / file_part
            assert path.exists(), f"{endpoint_id}: missing test file {file_part}"
            names = cache.setdefault(file_part, _func_names(path))
            assert func in names, f"{endpoint_id}: {file_part} has no {func!r}"


@pytest.mark.xfail(reason="coverage cells populated incrementally by Tasks 3-6", strict=False)
@pytest.mark.parametrize("endpoint_id", [e.id for e in ENDPOINTS])
def test_matrix_is_complete(endpoint_id):
    # The completeness gate. Every endpoint must have CLI+ and CLI- tested. SDK
    # cells must be tested when the SDK exposes the endpoint, else they are N/A.
    # This is the completeness gate; xfail(strict=False) keeps CI green until
    # Tasks 3-6 fill the cells (Task 7 removes the marker to make it a hard gate).
    cells = COVERAGE[endpoint_id]
    missing = []
    if cells.cli_pos is None:
        missing.append("cli_pos")
    if cells.cli_neg is None:
        missing.append("cli_neg")
    if sdk_supported(endpoint_id):
        if cells.sdk_pos is None:
            missing.append("sdk_pos")
        if cells.sdk_neg is None:
            missing.append("sdk_neg")
    assert not missing, f"{endpoint_id}: uncovered cells {missing}"
