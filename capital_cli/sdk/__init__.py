"""Capital.com SDK — public API, stable within 0.x (frozen at 1.0).

    from capital_cli.sdk import CapitalComApp, CapitalComConfig, RiskPolicy
"""

from capital_cli.sdk.app import CapitalComApp
from capital_cli.sdk.config import CapitalComConfig
from capital_cli.sdk.risk_policy import RiskPolicy

__all__ = ["CapitalComApp", "CapitalComConfig", "RiskPolicy"]
