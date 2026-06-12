"""Configuration for the Capital.com CLI (env-file aware)."""

import logging
import os
from enum import Enum
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CapEnv(str, Enum):
    """Capital.com environment."""

    DEMO = "demo"
    LIVE = "live"


def _resolve_env_file() -> str | None:
    """
    Resolve which .env file to load.

    Order: $CAP_ENV_FILE > ./.env > ~/.config/capital-cli/.env > None.
    """
    explicit = os.environ.get("CAP_ENV_FILE")
    if explicit:
        return explicit
    candidates = [
        Path.cwd() / ".env",
        Path.home() / ".config" / "capital-cli" / ".env",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


class Config(BaseSettings):
    """Application configuration loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Required credentials
    cap_env: CapEnv = Field(default=CapEnv.DEMO, description="Environment: demo or live")
    cap_api_key: str = Field(..., description="API Key from Capital.com")
    cap_identifier: str = Field(..., description="Login email")
    cap_api_password: str = Field(..., description="API Key custom password")

    # Trading safety controls
    cap_allow_trading: bool = Field(default=False)
    cap_allowed_epics: str = Field(default="")
    cap_max_position_size: float = Field(default=1.0, gt=0)
    cap_max_working_order_size: float = Field(default=1.0, gt=0)
    cap_max_open_positions: int = Field(default=3, ge=0)
    cap_max_orders_per_day: int = Field(default=20, ge=0)
    cap_require_explicit_confirm: bool = Field(default=True)
    cap_dry_run: bool = Field(default=False)

    # Optional account/session
    cap_default_account_id: str | None = Field(default=None)
    cap_http_timeout_s: float = Field(default=15.0, gt=0)
    cap_log_level: str = Field(default="WARNING")
    cap_ws_enabled: bool = Field(default=False)

    # Internal defaults
    cap_preview_cache_ttl_s: int = Field(default=120)
    cap_ping_interval_s: int = Field(default=480)

    @field_validator("cap_log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper_v = v.upper()
        if upper_v not in valid:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid}")
        return upper_v

    @model_validator(mode="after")
    def validate_trading_config(self) -> "Config":
        if self.cap_allow_trading and not self.cap_allowed_epics.strip():
            raise ValueError(
                "CAP_ALLOW_TRADING is true but CAP_ALLOWED_EPICS is empty. "
                "Specify allowed EPICs (or 'ALL' for unrestricted)."
            )
        return self

    @property
    def base_url(self) -> str:
        if self.cap_env == CapEnv.DEMO:
            return "https://demo-api-capital.backend-capital.com"
        return "https://api-capital.backend-capital.com"

    @property
    def api_base_url(self) -> str:
        return f"{self.base_url}/api/v1"

    @property
    def ws_url(self) -> str:
        return "wss://api-streaming-capital.backend-capital.com/connect"

    @property
    def allowed_epics_list(self) -> list[str]:
        if not self.cap_allowed_epics.strip():
            return []
        return [e.strip() for e in self.cap_allowed_epics.split(",") if e.strip()]

    def is_epic_allowed(self, epic: str) -> bool:
        if not self.cap_allow_trading:
            return False
        allowed = self.allowed_epics_list
        if not allowed:
            return False
        if allowed[0].upper() == "ALL":
            return True
        return epic.upper() in [e.upper() for e in allowed]

    def setup_logging(self) -> None:
        logging.basicConfig(
            level=getattr(logging, self.cap_log_level),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("websockets").setLevel(logging.WARNING)


_config: Config | None = None


def get_config() -> Config:
    """Get or lazily build the global config from the resolved env file."""
    global _config
    if _config is None:
        _config = Config(_env_file=_resolve_env_file())  # type: ignore[call-arg]
        _config.setup_logging()
    return _config


def set_config(config: Config) -> None:
    """Inject a pre-built config (used by tests and the CLI root callback)."""
    global _config
    _config = config


def reset_config() -> None:
    """Reset the global config (forces re-read on next get_config())."""
    global _config
    _config = None
