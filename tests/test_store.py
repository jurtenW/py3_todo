import json
from pathlib import Path

import pytest

from clicktodo.models import default_state, normalize_state
from clicktodo.store import TodoStore


@pytest.fixture
def store_path(tmp_path: Path) -> Path:
    return tmp_path / "todos.json"


@pytest.fixture
def store(store_path: Path) -> TodoStore:
    s = TodoStore(store_path)
    s.ensure_file()
    return s


def test_default_state_keys():
    state = default_state()
    assert "todos" in state
    assert "long-term" in state
    assert "archived" in state


def test_normalize_preserves_clock():
    raw = {**default_state(), "clock": {"running": True}}
    merged = normalize_state(raw)
    assert merged["clock"]["running"] is True


def test_atomic_save(store: TodoStore):
    store.add_todo("Task A", "01.01.2026")
    assert store.filepath.exists()
    data = json.loads(store.filepath.read_text(encoding="utf-8"))
    assert len(data["todos"]) == 1
    assert not store.filepath.with_suffix(store.filepath.suffix + ".tmp").exists()


def test_add_and_archive(store: TodoStore):
    item = store.add_todo("Done task")
    item.done = True
    store.update_todo(item)
    store.archive_finished_todos()
    assert len(store.get_todos()) == 0
    assert len(store.data["archived"]) == 1


def test_restore_archived(store: TodoStore):
    item = store.add_todo("Restore me")
    store.archive_todo(item)
    archived = store.get_archived_items()
    store.restore_archived(archived[0].id)
    assert len(store.get_todos()) == 1
    assert store.get_todos()[0].done is False


def test_undo_last_done(store: TodoStore):
    a = store.add_todo("A")
    b = store.add_todo("B")
    b.done = True
    store.update_todo(b)
    assert store.undo_last_done()
    assert not store.get_todos()[-1].done


def test_long_term_promote(store: TodoStore):
    store.add_long_term("Backlog item")
    store.promote_long_term(0)
    assert len(store.get_long_term()) == 0
    assert len(store.get_todos()) == 1
    assert store.get_todos()[0].text == "Backlog item"
