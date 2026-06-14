"""Tests for the opt-in JSONL audit log of trade mutations (CAP_AUDIT_LOG)."""

import json

from capital_cli.core.audit import audit_mutation


def test_audit_writes_jsonl_line(tmp_path, monkeypatch):
    path = tmp_path / "sub" / "audit.log"
    monkeypatch.setenv("CAP_AUDIT_LOG", str(path))

    audit_mutation(
        command="execute-position",
        env="demo",
        account="ACC1",
        epic="GOLD",
        size=1.0,
        preview_id="pv_123",
        deal_reference="o_abc",
        status="ACCEPTED",
    )

    assert path.exists()
    lines = path.read_text().strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["command"] == "execute-position"
    assert record["env"] == "demo"
    assert record["account"] == "ACC1"
    assert record["epic"] == "GOLD"
    assert record["size"] == 1.0
    assert record["preview_id"] == "pv_123"
    assert record["deal_reference"] == "o_abc"
    assert record["status"] == "ACCEPTED"
    assert "timestamp" in record
    # No secrets anywhere in the line.
    blob = lines[0].lower()
    for secret in ("password", "api_key", "cst", "security-token"):
        assert secret not in blob


def test_audit_appends(tmp_path, monkeypatch):
    path = tmp_path / "audit.log"
    monkeypatch.setenv("CAP_AUDIT_LOG", str(path))
    audit_mutation(command="close", env="demo", account="ACC1", status="ACCEPTED")
    audit_mutation(command="cancel", env="demo", account="ACC1", status="ACCEPTED")
    lines = path.read_text().strip().splitlines()
    assert len(lines) == 2


def test_audit_disabled_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("CAP_AUDIT_LOG", raising=False)
    path = tmp_path / "audit.log"
    audit_mutation(command="execute-position", env="demo", account="ACC1", status="ACCEPTED")
    assert not path.exists()


def test_audit_omits_none_optional_fields(tmp_path, monkeypatch):
    path = tmp_path / "audit.log"
    monkeypatch.setenv("CAP_AUDIT_LOG", str(path))
    audit_mutation(command="close", env="demo", account="ACC1", status="ACCEPTED")
    record = json.loads(path.read_text().strip())
    # epic/size/preview_id were not provided -> not present (kept clean).
    assert "epic" not in record
    assert "size" not in record
    assert "preview_id" not in record
