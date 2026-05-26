"""Todo item and JSON document schema."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

# Current schema version – increment when the JSON layout changes.
SCHEMA_VERSION: int = 1
_MIGRATIONS: list[Callable[[dict[str, Any]], None]] = []


def register_migration(fn: Callable[[dict[str, Any]], None]) -> Callable[[dict[str, Any]], None]:
    """Decorator to register a state-migration function."""
    _MIGRATIONS.append(fn)
    return fn


@dataclass
class Environment:
    """Execution context for a Todo (e.g. a project directory)."""

    path: str


@dataclass
class TodoItem:
    id: int
    text: str
    done: bool = False
    date: str | None = None
    created_at: int = 0
    environment: Environment | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TodoItem:
        env: Environment | None = None
        raw_env = data.get("environment")
        if isinstance(raw_env, dict):
            raw_path = raw_env.get("path")
            if isinstance(raw_path, str) and raw_path:
                env = Environment(path=raw_path)
        return cls(
            id=data.get("idx", 0),
            text=data.get("text", ""),
            done=data.get("done", False),
            date=data.get("date"),
            created_at=data.get("time", 0),
            environment=env,
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "idx": self.id,
            "text": self.text,
            "done": self.done,
            "date": self.date,
            "time": self.created_at,
        }
        if self.environment is not None:
            payload["environment"] = {"path": self.environment.path}
        return payload


def default_state() -> dict[str, Any]:
    return {
        "version": SCHEMA_VERSION,
        "todos": [],
        "archived": [],
        "long-term": [],
        "display_id": 0,
        "seq": 0,
    }


def normalize_state(data: dict[str, Any]) -> dict[str, Any]:
    """Ensure required keys exist; run migrations; preserve optional keys."""
    current_version = data.get("version", 0)

    # Run registered migrations sequentially from current_version → SCHEMA_VERSION.
    # Migration at index i upgrades from version i to i+1.
    for migration_index in range(current_version, SCHEMA_VERSION):
        if migration_index < len(_MIGRATIONS):
            _MIGRATIONS[migration_index](data)

    data["version"] = SCHEMA_VERSION

    base = default_state()
    merged = {**base, **data}
    merged.setdefault("todos", [])
    merged.setdefault("archived", [])
    merged.setdefault("long-term", [])
    merged["todos"] = list(merged.get("todos") or [])
    merged["archived"] = list(merged.get("archived") or [])
    merged["long-term"] = list(merged.get("long-term") or [])
    return merged


def open_todos(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [t for t in data.get("todos", []) if not t.get("done")]
