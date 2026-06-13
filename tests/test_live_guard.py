"""warn_if_live prints a stderr banner only when CAP_ENV=live."""

from capital_cli.cli.live_guard import warn_if_live
from capital_cli.cli.output import Output
from capital_cli.core.config import CapEnv, Config, reset_config, set_config


def _cfg(env: CapEnv) -> Config:
    return Config(
        cap_env=env,
        cap_api_key="k",
        cap_identifier="i@example.com",
        cap_api_password="p",
    )


def test_banner_on_live(capsys):
    set_config(_cfg(CapEnv.LIVE))
    try:
        warn_if_live(Output())
        err = capsys.readouterr().err
        assert "LIVE" in err
    finally:
        reset_config()


def test_no_banner_on_demo(capsys):
    set_config(_cfg(CapEnv.DEMO))
    try:
        warn_if_live(Output())
        assert capsys.readouterr().err.strip() == ""
    finally:
        reset_config()
