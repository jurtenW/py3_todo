"""Todo item and JSON document schema."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Current schema version – increment when the JSON layout changes.
SCHEMA_VERSION: int = 3
_MIGRATIONS: list[Callable[[dict[str, Any]], None]] = []


def register_migration(fn: Callable[[dict[str, Any]], None]) -> Callable[[dict[str, Any]], None]:
    """Decorator to register a state-migration function."""
    _MIGRATIONS.append(fn)
    return fn


@register_migration
def _migration_v1_to_v2(data: dict[str, Any]) -> None:
    """Version 1 → 2: opens list is new; old todos just get default []."""
    pass


@register_migration
def _migration_v2_to_v3(data: dict[str, Any]) -> None:
    """Version 2 → 3: convert environment path into an OpenItem."""
    for todos_key in ("todos", "archived", "long-term"):
        todos_list = data.get(todos_key) or []
        for todo in todos_list:
            env = todo.get("environment")
            if not isinstance(env, dict):
                continue
            raw_path = env.get("path")
            if not isinstance(raw_path, str) or not raw_path:
                continue
            existing_opens = env.get("opens")
            if not isinstance(existing_opens, list):
                env["opens"] = []
                existing_opens = env["opens"]
            # Only auto-migrate if opens is empty (avoid duplicates).
            if not existing_opens:
                existing_opens.append({"path": raw_path, "app": "code"})
            del env["path"]


class AppLauncher(Enum):
    """Fixed preset of applications that can open files/URLs."""

    FIREFOX = "firefox"
    CODE = "code"
    CURSOR = "cursor"
    OKULAR = "okular"
    REMNOTE = "RemNote.AppImage"

    @classmethod
    def from_string(cls, value: str) -> "AppLauncher":
        """Look up by value string; return CODE on miss."""
        try:
            return cls(value=value)
        except ValueError:
            return cls.CODE

    @classmethod
    def guess_for_path(cls, path: str) -> "AppLauncher":
        """Guess the best launcher for a path/URL based on extension."""
        if path.startswith(("http://", "https://")):
            return cls.FIREFOX

        ext = _get_extension(path)
        if ext == ".pdf":
            return cls.OKULAR
        if ext in (".html", ".htm", ".url"):
            return cls.FIREFOX
        return cls.CODE


def _get_extension(path: str) -> str:
    """Return lowercase extension (e.g. '.pdf') or empty string."""
    dot = path.rfind(".")
    if dot == -1:
        return ""
    return path[dot:].lower()


@dataclass
class OpenItem:
    """A file, URL, or path to open with a specific application."""

    path: str
    app: AppLauncher


@dataclass
class Environment:
    """Items to open for a Todo."""

    opens: list[OpenItem] = field(default_factory=list)


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
            opens = []
            raw_opens = raw_env.get("opens")
            if isinstance(raw_opens, list):
                for entry in raw_opens:
                    if isinstance(entry, dict):
                        op = entry.get("path", "")
                        ap = entry.get("app", "")
                        if isinstance(op, str) and op:
                            opens.append(
                                OpenItem(
                                    path=op,
                                    app=AppLauncher.from_string(ap),
                                )
                            )
            # Legacy: if only "path" key exists (pre-migration), turn it into an OpenItem.
            if not opens:
                raw_path = raw_env.get("path")
                if isinstance(raw_path, str) and raw_path:
                    opens.append(OpenItem(path=raw_path, app=AppLauncher.CODE))
            if opens:
                env = Environment(opens=opens)
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
            env_payload: dict[str, Any] = {}
            if self.environment.opens:
                env_payload["opens"] = [
                    {"path": oi.path, "app": oi.app.value}
                    for oi in self.environment.opens
                ]
            if env_payload:
                payload["environment"] = env_payload
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
