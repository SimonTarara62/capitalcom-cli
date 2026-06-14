"""Secret redaction must mask the login identifier/email as well as passwords/tokens."""

from capital_cli.core.errors import redact_secrets


def test_redacts_identifier_and_password():
    out = redact_secrets({"identifier": "a@b.com", "password": "x"})
    assert out["identifier"] == "***REDACTED***"
    assert out["password"] == "***REDACTED***"


def test_redacts_email_field():
    out = redact_secrets({"email": "a@b.com", "ok": 1})
    assert out["email"] == "***REDACTED***"
    assert out["ok"] == 1


def test_redacts_login_request_body():
    # Mirrors the actual login body built in core/session.py.
    body = {"identifier": "trader@example.com", "password": "hunter2", "encryptedPassword": False}
    out = redact_secrets(body)
    assert out["identifier"] == "***REDACTED***"
    assert out["password"] == "***REDACTED***"


def test_still_redacts_tokens_and_keys():
    out = redact_secrets({"X-SECURITY-TOKEN": "t", "X-CAP-API-KEY": "k", "name": "ok"})
    assert out["X-SECURITY-TOKEN"] == "***REDACTED***"
    assert out["X-CAP-API-KEY"] == "***REDACTED***"
    assert out["name"] == "ok"


def test_redacts_nested():
    out = redact_secrets({"outer": {"identifier": "a@b.com"}})
    assert out["outer"]["identifier"] == "***REDACTED***"
