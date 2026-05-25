"""Status-bar display logic (no direct file I/O)."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from clicktodo.models import open_todos
from clicktodo.store import TodoStore


def todo_counts(data: Dict[str, Any]) -> Tuple[int, int]:
    todos = data.get("todos", [])
    done = sum(1 for t in todos if t.get("done"))
    return done, len(todos)


def truncate_text(text: str, max_width: int) -> str:
    if len(text) > max_width:
        return text[:max_width] + "…"
    return text


def get_display_item(store: TodoStore) -> Optional[Dict[str, Any]]:
    """
    Resolve the task shown on the bar from display_id.
    Falls back to the first open task and fixes display_id if stale.
    """
    data = store.data
    display_id = data.get("display_id", 0)
    opens = open_todos(data)
    if not opens:
        return None

    for t in opens:
        if t.get("idx") == display_id:
            return t

    data["display_id"] = opens[0].get("idx")
    store.save()
    return opens[0]


def cycle_display(store: TodoStore, direction: int) -> None:
    """Rotate display_id among open tasks."""
    data = store.data
    opens = open_todos(data)
    if not opens:
        return

    current_id = data.get("display_id")
    current_idx = 0
    for i, t in enumerate(opens):
        if t.get("idx") == current_id:
            current_idx = i
            break

    new_idx = (current_idx + direction) % len(opens)
    data["display_id"] = opens[new_idx]["idx"]
    store.save()


def next_label(store: TodoStore, max_width: int) -> str:
    item = get_display_item(store)
    if not item:
        return "No Tasks"
    return truncate_text(item.get("text", ""), max_width)


def mark_displayed_done(store: TodoStore) -> bool:
    item = get_display_item(store)
    if not item:
        return False
    store.mark_done_by_idx(item["idx"])
    return True
