import json

from capital_cli.cli.app import app


def test_status_json(runner, mock_session):
    result = runner.invoke(app, ["--json", "session", "status"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["account_id"] == "ACC1"


def test_status_table(runner, mock_session):
    result = runner.invoke(app, ["session", "status"])
    assert result.exit_code == 0
    assert "ACC1" in result.stdout


def test_login_calls_core(runner, mock_session):
    result = runner.invoke(app, ["session", "login", "--force"])
    assert result.exit_code == 0
    mock_session.login.assert_awaited_once()
    assert mock_session.login.await_args.kwargs["force"] is True


def test_ping(runner, mock_session):
    result = runner.invoke(app, ["--json", "session", "ping"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["status"] == "OK"


def test_logout(runner, mock_session):
    result = runner.invoke(app, ["session", "logout"])
    assert result.exit_code == 0
    mock_session.logout.assert_awaited_once()


def test_switch(runner, mock_session):
    result = runner.invoke(app, ["session", "switch", "ACC2"])
    assert result.exit_code == 0
    mock_session.switch_account.assert_awaited_once_with("ACC2")
