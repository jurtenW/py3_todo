"""Path helpers for module root, config paths, and XDG data."""

from __future__ import annotations

import os
from pathlib import Path

_MODULE_DIR = Path(__file__).resolve().parents[2]


def module_root() -> Path:
    """Repository / package root (parent of src/clicktodo)."""
    return _MODULE_DIR


def default_data_path() -> Path:
    """Default user data file: XDG_DATA_HOME/clicktodo/todos.json."""
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        base = Path(xdg).expanduser()
    else:
        base = Path.home() / ".local" / "share"
    return base / "clicktodo" / "todos.json"


def resolve_path(configured: str, base: Path | None = None) -> Path:
    """Resolve a path relative to base (defaults to module root)."""
    path = Path(configured).expanduser()
    if path.is_absolute():
        return path
    root = base if base is not None else module_root()
    return root / path
