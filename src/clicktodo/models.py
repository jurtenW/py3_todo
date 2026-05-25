"""Todo item and JSON document schema."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class TodoItem:
    id: int
    text: str
    done: bool = False
    date: Optional[str] = None
    created_at: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TodoItem:
        return cls(
            id=data.get("idx", 0),
            text=data.get("text", ""),
            done=data.get("done", False),
            date=data.get("date"),
            created_at=data.get("time", 0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "idx": self.id,
            "text": self.text,
            "done": self.done,
            "date": self.date,
            "time": self.created_at,
        }


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
