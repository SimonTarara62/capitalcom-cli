import pytest
import typer

from capital_cli.cli.output import Output
from capital_cli.cli.runner import EXIT_CODES, run
from capital_cli.core.errors import ErrorCode, SessionError, TradingDisabledError


def test_run_returns_coroutine_result():
    out = Output(json_mode=True)

    async def _do():
        return {"ok": 1}

    assert run(out, _do) == {"ok": 1}


def test_run_maps_capital_error_to_exit_code():
    out = Output(json_mode=True)

    async def _do():
        raise TradingDisabledError()

    with pytest.raises(typer.Exit) as exc:
        run(out, _do)
    assert exc.value.exit_code == EXIT_CODES[ErrorCode.TRADING_DISABLED]


def test_run_maps_session_error():
    out = Output(json_mode=True)

    async def _do():
        raise SessionError("nope", code=ErrorCode.AUTH_FAILED)

    with pytest.raises(typer.Exit) as exc:
        run(out, _do)
    assert exc.value.exit_code == EXIT_CODES[ErrorCode.AUTH_FAILED]


def test_run_maps_unknown_exception_to_one():
    out = Output(json_mode=True)

    async def _do():
        raise RuntimeError("kaboom")

    with pytest.raises(typer.Exit) as exc:
        run(out, _do)
    assert exc.value.exit_code == 1


def test_run_maps_validation_error_to_two():
    from capital_cli.core.models import PreviewPositionRequest

    out = Output(json_mode=True)

    async def _do():
        # size has gt=0; -1 raises pydantic ValidationError.
        PreviewPositionRequest(epic="GOLD", direction="BUY", size=-1)
        return {}

    with pytest.raises(typer.Exit) as exc:
        run(out, _do)
    assert exc.value.exit_code == EXIT_CODES[ErrorCode.INVALID_REQUEST]


def test_init_state_applies_env_overrides(monkeypatch, tmp_path):
    from capital_cli.cli.context import init_state

    env = tmp_path / "x.env"
    env.write_text("CAP_API_KEY=k\nCAP_IDENTIFIER=a@b.c\nCAP_API_PASSWORD=p\n")
    state = init_state(
        json_mode=True, env_file=env, env="live", account="ACC9", verbose=False
    )
    import os

    assert os.environ["CAP_ENV_FILE"] == str(env)
    assert os.environ["CAP_ENV"] == "live"
    assert os.environ["CAP_DEFAULT_ACCOUNT_ID"] == "ACC9"
    assert state.out.json_mode is True

    # init_state writes os.environ directly; scrub so later tests are unaffected.
    for var in ("CAP_ENV", "CAP_DEFAULT_ACCOUNT_ID"):
        os.environ.pop(var, None)
