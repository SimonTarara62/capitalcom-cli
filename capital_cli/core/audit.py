"""Opt-in JSONL audit log of executed trade mutations.

Disabled by default. When the ``CAP_AUDIT_LOG`` environment variable points at a
file path, every executed mutation (execute-position/order, close, cancel,
amend-position/order) appends ONE JSON line describing the action and its broker
outcome. The line never contains secrets (no API keys, passwords, or session
tokens) — only the command, environment, account id, and deal identifiers.

The writer is intentionally tiny and best-effort: an audit-log failure must
never break a trade command, so write errors are swallowed.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_AUDIT_ENV_VAR = "CAP_AUDIT_LOG"


def audit_mutation(
    *,
    command: str,
    env: str,
    account: str | None,
    status: str,
    epic: str | None = None,
    size: float | None = None,
    preview_id: str | None = None,
    deal_reference: str | None = None,
) -> None:
    """Append one JSONL audit line if CAP_AUDIT_LOG is set; otherwise no-op.

    Optional fields (``epic``/``size``/``preview_id``/``deal_reference``) are
    omitted when ``None`` to keep the line clean. Never raises — a logging
    failure must not affect the trade result.
    """
    path_str = os.environ.get(_AUDIT_ENV_VAR)
    if not path_str:
        return

    record: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "env": env,
        "account": account,
    }
    if epic is not None:
        record["epic"] = epic
    if size is not None:
        record["size"] = size
    if preview_id is not None:
        record["preview_id"] = preview_id
    if deal_reference is not None:
        record["deal_reference"] = deal_reference
    record["status"] = status

    try:
        path = Path(path_str)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Append a single line. 'a' + one write() is atomic enough for line-sized
        # appends on POSIX; a partial line is preferable to a lost trade record.
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, default=str) + "\n")
    except Exception as exc:  # noqa: BLE001 - best-effort: an audit-log failure
        # must NEVER abort or alter a real trade, so swallow ANY error (not just
        # OSError — e.g. an unexpected serialization/typing error) after logging.
        logger.warning("Failed to write audit log to %s: %s", path_str, exc)
