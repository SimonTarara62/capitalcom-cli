"""StateStore persistence and cross-process RiskEngine preview flow."""

from datetime import datetime, timedelta, timezone

import pytest

from capital_cli.core.models import PreviewResult


@pytest.fixture
def state_file(tmp_path, monkeypatch):
    path = tmp_path / "state.json"
    monkeypatch.setenv("CAPCTL_STATE_FILE", str(path))
    from capital_cli.core.state import reset_state_store

    reset_state_store()
    yield path
    reset_state_store()


def _make_preview(**overrides) -> PreviewResult:
    defaults: dict = {
        "normalized_request": {"epic": "GOLD"},
        "checks": [],
        "all_checks_passed": True,
    }
    defaults.update(overrides)
    return PreviewResult(**defaults)


def test_preview_round_trip_across_instances(state_file):
    from capital_cli.core.state import StateStore

    preview = _make_preview()
    StateStore().save_preview(preview)

    # Fresh instance simulates a new CLI process.
    loaded = StateStore().load_preview(preview.preview_id)
    assert loaded is not None
    assert loaded.preview_id == preview.preview_id
    assert loaded.normalized_request == {"epic": "GOLD"}
    assert loaded.all_checks_passed is True


def test_load_missing_preview_returns_none(state_file):
    from capital_cli.core.state import StateStore

    assert StateStore().load_preview("nope") is None


def test_delete_preview(state_file):
    from capital_cli.core.state import StateStore

    preview = _make_preview()
    store = StateStore()
    store.save_preview(preview)
    store.delete_preview(preview.preview_id)
    assert StateStore().load_preview(preview.preview_id) is None


def test_order_counter_accumulates_and_resets_by_date(state_file):
    from capital_cli.core.state import StateStore

    store = StateStore()
    assert store.get_order_count("2026-06-12") == 0
    store.increment_order_count("2026-06-12")
    store.increment_order_count("2026-06-12")
    assert StateStore().get_order_count("2026-06-12") == 2
    # A new date starts from zero.
    assert StateStore().get_order_count("2026-06-13") == 0
    StateStore().increment_order_count("2026-06-13")
    assert StateStore().get_order_count("2026-06-13") == 1


def test_risk_engine_reads_preview_saved_by_another_engine(state_file):
    from capital_cli.core.risk import RiskEngine

    preview = _make_preview()
    engine_a = RiskEngine()
    engine_a.state.save_preview(preview)

    engine_b = RiskEngine()  # fresh engine = fresh process
    loaded = engine_b.get_preview(preview.preview_id)
    assert loaded.preview_id == preview.preview_id


def test_risk_engine_rejects_expired_persisted_preview(state_file):
    from capital_cli.core.errors import PreviewError
    from capital_cli.core.risk import RiskEngine

    stale = _make_preview(created_at=datetime.now(timezone.utc) - timedelta(seconds=600))
    RiskEngine().state.save_preview(stale)
    with pytest.raises(PreviewError):
        RiskEngine().get_preview(stale.preview_id)


def test_risk_engine_daily_counter_uses_store(state_file):
    from capital_cli.core.risk import RiskEngine

    RiskEngine().increment_order_count()
    check = RiskEngine()._check_daily_limit()
    assert check.passed is True
    assert "1/" in check.message
