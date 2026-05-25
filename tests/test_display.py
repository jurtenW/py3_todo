from pathlib import Path

import pytest

from clicktodo import display
from clicktodo.store import TodoStore


@pytest.fixture
def store(tmp_path: Path) -> TodoStore:
    s = TodoStore(tmp_path / "todos.json")
    s.add_todo("First", "01.01.2026")
    s.add_todo("Second", "02.01.2026")
    return s


def test_cycle_display_wraps(store: TodoStore):
    store.data["display_id"] = store.get_todos()[0].id
    display.cycle_display(store, 1)
    assert store.data["display_id"] == store.get_todos()[1].id
    display.cycle_display(store, 1)
    assert store.data["display_id"] == store.get_todos()[0].id


def test_get_display_item_fallback(store: TodoStore):
    store.data["display_id"] = 99999
    item = display.get_display_item(store)
    assert item is not None
    assert store.data["display_id"] == item["idx"]


def test_todo_counts(store: TodoStore):
    todos = store.get_todos()
    todos[0].done = True
    store.update_todo(todos[0])
    done, total = display.todo_counts(store.data)
    assert done == 1
    assert total == 2
