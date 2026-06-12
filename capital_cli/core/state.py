"""Persistent CLI state shared across capctl invocations.

A single-shot CLI process cannot keep the preview cache or the daily order
counter in memory the way a long-lived server can, so both are stored in a
small JSON file (default: ~/.config/capital-cli/state.json; override with
the CAPCTL_STATE_FILE environment variable).
"""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
from typing import Any

from .models import PreviewResult


def _default_state_path() -> Path:
    override = os.environ.get("CAPCTL_STATE_FILE")
    if override:
        return Path(override)
    return Path.home() / ".config" / "capital-cli" / "state.json"


class StateStore:
    """Tiny JSON-file-backed store for previews and the daily order counter."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or _default_state_path()

    def _read(self) -> dict[str, Any]:
        try:
            return json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError):
            return {}

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(json.dumps(data, default=str))
        tmp.replace(self.path)
        with contextlib.suppress(OSError):
            self.path.chmod(0o600)

    # ----- previews -----

    def save_preview(self, preview: PreviewResult) -> None:
        data = self._read()
        previews = data.setdefault("previews", {})
        previews[preview.preview_id] = json.loads(preview.model_dump_json())
        self._write(data)

    def load_preview(self, preview_id: str) -> PreviewResult | None:
        raw = self._read().get("previews", {}).get(preview_id)
        if raw is None:
            return None
        try:
            return PreviewResult.model_validate(raw)
        except Exception:  # noqa: BLE001 - corrupt entry is equivalent to missing
            return None

    def delete_preview(self, preview_id: str) -> None:
        data = self._read()
        if data.get("previews", {}).pop(preview_id, None) is not None:
            self._write(data)

    # ----- daily order counter -----

    def get_order_count(self, date: str) -> int:
        counter = self._read().get("order_counter", {})
        return counter.get("count", 0) if counter.get("date") == date else 0

    def increment_order_count(self, date: str) -> None:
        data = self._read()
        counter = data.get("order_counter", {})
        count = counter.get("count", 0) if counter.get("date") == date else 0
        data["order_counter"] = {"date": date, "count": count + 1}
        self._write(data)


_state_store: StateStore | None = None


def get_state_store() -> StateStore:
    """Get or create the global state store instance."""
    global _state_store
    if _state_store is None:
        _state_store = StateStore()
    return _state_store


def reset_state_store() -> None:
    """Reset the global state store (mainly for testing)."""
    global _state_store
    _state_store = None
