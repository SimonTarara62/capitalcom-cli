"""Reusable, presentation-free Capital.com domain services.

These compose the core/ primitives (config, http client, session, risk, state)
into per-domain operations with structured returns and no Typer/Rich. The CLI
and the SDK facade (capital_cli.sdk) both build on them.
"""
