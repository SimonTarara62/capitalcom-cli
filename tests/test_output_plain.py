"""--plain renders tab-delimited rows parseable by cut -f; JSON still wins."""

from capital_cli.cli.output import Output


def test_plain_rows_tab_delimited(capsys):
    out = Output(plain=True)
    out.rows([{"epic": "GOLD", "bid": 2331.05}], ["epic", "bid"])
    captured = capsys.readouterr().out
    assert captured.strip() == "GOLD\t2331.05"


def test_plain_record_tab_delimited(capsys):
    out = Output(plain=True)
    out.record({"epic": "GOLD", "bid": 2331.05})
    lines = capsys.readouterr().out.strip().splitlines()
    assert "epic\tGOLD" in lines
    assert "bid\t2331.05" in lines


def test_json_mode_overrides_plain(capsys):
    out = Output(json_mode=True, plain=True)
    out.rows([{"epic": "GOLD"}], ["epic"])
    captured = capsys.readouterr().out
    assert '"epic"' in captured  # JSON document, not a tab row
