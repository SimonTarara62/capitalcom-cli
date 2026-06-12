import json

from rich.console import Console

from capital_cli.cli.output import Output


def _capture(out: Output) -> str:
    return out.console.export_text()


def test_record_json_mode_emits_valid_json():
    out = Output(json_mode=True)
    out.console = Console(record=True, width=120)
    out.record({"a": 1, "b": True}, title="X")
    text = _capture(out)
    assert json.loads(text) == {"a": 1, "b": True}


def test_record_table_mode_contains_keys():
    out = Output(json_mode=False)
    out.console = Console(record=True, width=120)
    out.record({"account_id": "ABC123"}, title="Session")
    text = _capture(out)
    assert "account_id" in text
    assert "ABC123" in text


def test_rows_json_mode_emits_list():
    out = Output(json_mode=True)
    out.console = Console(record=True, width=120)
    out.rows([{"epic": "GOLD", "bid": 1}, {"epic": "SILVER", "bid": 2}], ["epic", "bid"])
    text = _capture(out)
    assert json.loads(text) == [{"epic": "GOLD", "bid": 1}, {"epic": "SILVER", "bid": 2}]


def test_rows_table_mode_renders_columns():
    out = Output(json_mode=False)
    out.console = Console(record=True, width=120)
    out.rows([{"epic": "GOLD", "bid": 1}], ["epic", "bid"], title="Markets")
    text = _capture(out)
    assert "GOLD" in text


def test_bool_formatting():
    from capital_cli.cli.output import _fmt

    assert _fmt(True) == "✓"
    assert _fmt(False) == "✗"
    assert _fmt(None) == "-"
