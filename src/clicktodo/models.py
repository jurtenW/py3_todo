"""Todo item and JSON document schema."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Environment:
    """Execution context for a Todo (e.g. a project directory)."""

    path: str


@dataclass
class TodoItem:
    id: int
    text: str
    done: bool = False
    date: Optional[str] = None
    created_at: int = 0
    environment: Optional[Environment] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TodoItem:
        env: Optional[Environment] = None
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

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "idx": self.id,
            "text": self.text,
            "done": self.done,
            "date": self.date,
            "time": self.created_at,
        }
        if self.environment is not None:
            payload["environment"] = {"path": self.environment.path}
        return payload


def default_state() -> Dict[str, Any]:
    return {
        "todos": [],
        "archived": [],
        "long-term": [],
        "display_id": 0,
        "seq": 0,
    }


def normalize_state(data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure required keys exist; preserve optional keys like clock."""
    base = default_state()
    merged = {**base, **data}
    merged.setdefault("todos", [])
    merged.setdefault("archived", [])
    merged.setdefault("long-term", [])
    merged["todos"] = list(merged.get("todos") or [])
    merged["archived"] = list(merged.get("archived") or [])
    merged["long-term"] = list(merged.get("long-term") or [])
    return merged


def open_todos(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [t for t in data.get("todos", []) if not t.get("done")]
