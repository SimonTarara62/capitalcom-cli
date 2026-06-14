"""E2E tests hit the real demo API. The root conftest's autouse `_credentials`
fixture points config at a dummy env file (for offline isolation); for in-process
e2e (the SDK facade tests) we must instead read the real repo-root .env so the
real credentials and trading flags apply. This fixture runs after the root one
(deeper conftest) and re-points CAP_ENV_FILE accordingly. The CLI e2e
(test_demo_e2e.py) is unaffected — it passes CAP_ENV_FILE to its subprocesses
explicitly."""

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ENV_FILE = REPO / ".env"


@pytest.fixture(autouse=True)
def _use_real_env(monkeypatch):
    if ENV_FILE.exists():
        monkeypatch.setenv("CAP_ENV_FILE", str(ENV_FILE))
        from capital_cli.core.config import reset_config

        reset_config()
    yield
    if ENV_FILE.exists():
        from capital_cli.core.config import reset_config

        reset_config()
