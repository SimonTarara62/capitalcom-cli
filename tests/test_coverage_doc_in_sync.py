"""Assert the committed coverage matrix + badge match the registry renderer, so
docs/api-coverage.md and docs/coverage-badge.json can never silently rot."""

import json
from pathlib import Path

from tools.render_coverage import MARKER, render

REPO = Path(__file__).resolve().parents[1]


def test_matrix_table_in_sync():
    table_md, _ = render()
    committed = (REPO / "docs" / "api-coverage.md").read_text()
    assert MARKER in committed, "run: python tools/render_coverage.py"
    assert committed.split(MARKER, 1)[1].strip() == table_md.split(MARKER, 1)[1].strip(), (
        "docs/api-coverage.md is stale — run: python tools/render_coverage.py"
    )


def test_badge_json_in_sync():
    _, badge_json = render()
    committed = (REPO / "docs" / "coverage-badge.json").read_text()
    assert json.loads(committed) == json.loads(badge_json), (
        "docs/coverage-badge.json is stale — run: python tools/render_coverage.py"
    )


def test_full_coverage_reached():
    _, badge_json = render()
    assert json.loads(badge_json)["message"].endswith("(100%)"), (
        "coverage matrix is not 100% — fill remaining cells"
    )
