"""Factory functions for creating test data."""

from __future__ import annotations

from typing import Any, Dict, List

from clicktodo.models import Environment, OpenItem, TodoItem, default_state


def make_todo_item(
    idx: int = 1,
    text: str = "Test task",
    done: bool = False,
    date: str | None = None,
    created_at: int = 0,
    environment: Environment | None = None,
) -> TodoItem:
    return TodoItem(
        id=idx,
        text=text,
        done=done,
        date=date,
        created_at=created_at,
        environment=environment,
    )


def make_todo_dict(
    idx: int = 1,
    text: str = "Test task",
    done: bool = False,
    date: str | None = None,
    time: int = 0,
    environment: Dict[str, str] | None = None,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "idx": idx,
        "text": text,
        "done": done,
        "date": date,
        "time": time,
    }
    if environment is not None:
        result["environment"] = environment
    return result


def make_state(
    todos: List[Dict[str, Any]] | None = None,
    archived: List[Dict[str, Any]] | None = None,
    long_term: List[Dict[str, Any]] | None = None,
    display_id: int = 0,
    seq: int = 0,
    version: int = 1,
    extra: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build a complete state dict with sensible defaults."""
    base = default_state()
    result: Dict[str, Any] = {**base}
    result["version"] = version
    if todos is not None:
        result["todos"] = todos
    if archived is not None:
        result["archived"] = archived
    if long_term is not None:
        result["long-term"] = long_term
    result["display_id"] = display_id
    result["seq"] = seq
    if extra:
        result.update(extra)
    return result


def sample_open_todo(idx: int = 1) -> Dict[str, Any]:
    return make_todo_dict(idx=idx, text="Open task", date="15.06.2026")


def sample_done_todo(idx: int = 2) -> Dict[str, Any]:
    return make_todo_dict(idx=idx, text="Done task", done=True, date="10.06.2026")


def sample_todo_with_env(idx: int = 3) -> Dict[str, Any]:
    return make_todo_dict(
        idx=idx,
        text="Project task",
        date="20.06.2026",
        environment={
            "opens": [{"path": "/home/user/project", "app": "code"}],
        },
    )


def sample_long_term_entry(text: str = "Someday idea") -> Dict[str, Any]:
    return {"text": text}


def sample_clock() -> Dict[str, Any]:
    return {
        "running": False,
        "timer_id": 0,
        "elapsed": 0.0,
        "start": 0.0,
    }


def sample_archive_entry(idx: int = 4) -> Dict[str, Any]:
    return make_todo_dict(idx=idx, text="Archived task", done=True)
