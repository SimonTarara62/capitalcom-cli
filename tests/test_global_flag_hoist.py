from capital_cli.cli.app import _hoist_global_flags

def test_hoist_moves_trailing_json_to_front():
    argv = ["capctl", "session", "status", "--json"]
    assert _hoist_global_flags(argv) == ["capctl", "--json", "session", "status"]

def test_hoist_is_noop_when_already_front():
    argv = ["capctl", "--json", "session", "status"]
    assert _hoist_global_flags(argv) == argv

def test_hoist_handles_multiple_flags():
    argv = ["capctl", "market", "search", "gold", "--plain", "--no-color"]
    out = _hoist_global_flags(argv)
    assert out[:3] == ["capctl", "--plain", "--no-color"] or out[:3] == ["capctl", "--no-color", "--plain"]
    assert "search" in out and "gold" in out

def test_hoist_does_not_touch_unrelated_flags():
    argv = ["capctl", "market", "prices", "GOLD", "--resolution", "HOUR"]
    assert _hoist_global_flags(argv) == argv
