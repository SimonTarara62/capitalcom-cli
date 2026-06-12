"""Output rendering: Rich tables for humans, raw JSON for scripts."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from rich.console import Console
from rich.table import Table


def _fmt(value: Any) -> str:
    """Format a scalar for table display."""
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "✓" if value else "✗"
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str)
    return str(value)


class Output:
    """Renders command results either as Rich tables or as JSON."""

    def __init__(self, json_mode: bool = False) -> None:
        self.json_mode = json_mode
        self.console = Console()
        self.err = Console(stderr=True)

    def _print_json(self, payload: Any) -> None:
        self.console.print_json(json.dumps(payload, default=str))

    def record(self, payload: dict[str, Any], *, title: str | None = None) -> None:
        """Render a single object as a two-column key/value table."""
        if self.json_mode:
            self._print_json(payload)
            return
        table = Table(show_header=False, title=title, title_justify="left", expand=False)
        table.add_column("Field", style="bold cyan", no_wrap=True)
        table.add_column("Value")
        for key, value in payload.items():
            table.add_row(str(key), _fmt(value))
        self.console.print(table)

    def rows(
        self,
        items: Sequence[dict[str, Any]],
        columns: Sequence[str],
        *,
        title: str | None = None,
    ) -> None:
        """Render a list of objects as a multi-column table."""
        if self.json_mode:
            self._print_json(list(items))
            return
        if not items:
            self.console.print("[dim]No results.[/]")
            return
        table = Table(title=title, title_justify="left", header_style="bold cyan")
        for col in columns:
            table.add_column(col)
        for item in items:
            table.add_row(*[_fmt(item.get(col)) for col in columns])
        self.console.print(table)

    def raw(self, payload: Any) -> None:
        """Print a payload as-is (JSON in json mode, pretty otherwise)."""
        if self.json_mode:
            self._print_json(payload)
        else:
            self.console.print(payload)

    def error(self, code: str, message: str) -> None:
        if self.json_mode:
            self.err.print_json(
                json.dumps({"ok": False, "error": {"code": code, "message": message}})
            )
        else:
            self.err.print(f"[bold red]Error[/] [dim]({code})[/]: {message}")

    def note(self, message: str) -> None:
        if not self.json_mode:
            self.err.print(f"[dim]{message}[/]")

    def success(self, message: str) -> None:
        if not self.json_mode:
            self.err.print(f"[green]✓[/] {message}")
