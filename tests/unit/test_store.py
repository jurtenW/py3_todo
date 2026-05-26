"""Edge-case tests for clicktodo.store."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any, Dict

import pytest

from clicktodo.models import Environment
from clicktodo.store import TodoStore
from tests.fixtures.data import (
    make_state,
    sample_done_todo,
    sample_long_term_entry,
    sample_open_todo,
    sample_todo_with_env,
)


# ---------------------------------------------------------------------------
# Loading edge cases
# ---------------------------------------------------------------------------

class TestStoreLoad:
    def test_missing_file_returns_default(self, tmp_path: Path):
        store = TodoStore(tmp_path / "nonexistent.json")
        assert store.data["todos"] == []

    def test_corrupted_json_returns_default(self, corrupted_file: Path):
        store = TodoStore(corrupted_file)
        assert store.data["todos"] == []

    def test_empty_file_returns_default(self, empty_file: Path):
        store = TodoStore(empty_file)
        assert store.data["todos"] == []

    def test_ensures_parent_directory(self, tmp_path: Path):
        fp = tmp_path / "deep" / "nested" / "todos.json"
        store = TodoStore(fp)
        store.ensure_file()
        assert fp.exists()
        assert fp.parent.is_dir()


# ---------------------------------------------------------------------------
# Save edge cases
# ---------------------------------------------------------------------------

class TestStoreSave:
    def test_atomic_save_no_tmp_left(self, store_path: Path):
        store = TodoStore(store_path)
        store.ensure_file()
        store.save()
        tmp = store_path.with_suffix(store_path.suffix + ".tmp")
        assert not tmp.exists()

    def test_save_with_indent(self, store_path: Path):
        store = TodoStore(store_path)
        store.ensure_file()
        store.save(indent=True)
        content = store_path.read_text(encoding="utf-8")
        assert "\n" in content

    def test_save_without_indent(self, store_path: Path):
        store = TodoStore(store_path)
        store.ensure_file()
        store.save(indent=False)
        content = store_path.read_text(encoding="utf-8")
        assert "\n" not in content

    def test_reload_picks_up_external_changes(self, store_path: Path):
        store = TodoStore(store_path)
        store.ensure_file()
        # Write externally.
        store_path.write_text(
            json.dumps({"todos": [{"idx": 99, "text": "external"}], "archived": [], "long-term": [], "display_id": 0, "seq": 0}),
            encoding="utf-8",
        )
        store.reload()
        assert any(t.get("idx") == 99 for t in store.data["todos"])

    def test_permission_error_on_save(self, tmp_path: Path):
        """Saving to a read-only directory raises PermissionError."""
        ro_dir = tmp_path / "readonly"
        ro_dir.mkdir()
        fp = ro_dir / "todos.json"
        # Create the store first, then restrict permissions.
        store = TodoStore(fp)
        store.ensure_file()
        # Make the directory read-only.
        ro_dir.chmod(0o444)
        try:
            with pytest.raises(PermissionError):
                store.add_todo("Fails")
        finally:
            ro_dir.chmod(0o755)


# ---------------------------------------------------------------------------
# CRUD edge cases
# ---------------------------------------------------------------------------

class TestCRUD:
    def test_add_empty_text(self, store_path: Path):
        store = TodoStore(store_path)
        item = store.add_todo("")
        assert item.text == ""
        assert len(store.get_todos()) == 1

    def test_update_nonexistent_id_noop(self, store_path: Path):
        store = TodoStore(store_path)
        store.ensure_file()
        phantom = Environment(path="/x")
        item = TodoItem(id=9999, text="ghost", environment=phantom)
        store.update_todo(item)  # should not crash
        assert len(store.get_todos()) == 0

    def test_delete_nonexistent_id_noop(self, store_path: Path):
        store = TodoStore(store_path)
        store.add_todo("Keep")
        count_before = len(store.get_todos())
        store.delete_todo(9999)
        assert len(store.get_todos()) == count_before

    def test_add_todo_increments_seq(self, store_path: Path):
        store = TodoStore(store_path)
        a = store.add_todo("A")
        b = store.add_todo("B")
        assert b.id == a.id + 1

    def test_seq_integrity_after_delete(self, store_path: Path):
        store = TodoStore(store_path)
        a = store.add_todo("A")
        b = store.add_todo("B")
        store.delete_todo(a.id)
        c = store.add_todo("C")
        assert c.id > b.id  # seq keeps increasing


# ---------------------------------------------------------------------------
# Archive edge cases
# ---------------------------------------------------------------------------

class TestArchive:
    def test_archive_then_restore_done_is_false(self, store_path: Path):
        store = TodoStore(store_path)
        item = store.add_todo("Temp")
        item.done = True
        store.update_todo(item)
        store.archive_todo(item)
        store.restore_archived(item.id)
        restored = store.get_todos()[0]
        assert restored.done is False

    def test_archive_preserves_id(self, store_path: Path):
        store = TodoStore(store_path)
        item = store.add_todo("Archive me")
        original_id = item.id
        store.archive_todo(item)
        archived = store.get_archived_items()
        assert len(archived) == 1
        assert archived[0].id == original_id

    def test_delete_archived_removes_permanently(self, store_path: Path):
        store = TodoStore(store_path)
        item = store.add_todo("Gone")
        store.archive_todo(item)
        store.delete_archived(item.id)
        assert len(store.get_archived_items()) == 0

    def test_delete_nonexistent_archived_id_noop(self, store_path: Path):
        store = TodoStore(store_path)
        store.ensure_file()
        store.delete_archived(9999)  # should not crash

    def test_restore_nonexistent_archived_noop(self, store_path: Path):
        store = TodoStore(store_path)
        store.ensure_file()
        store.restore_archived(9999)  # should not crash
        assert len(store.get_todos()) == 0


# ---------------------------------------------------------------------------
# Undo edge cases
# ---------------------------------------------------------------------------

class TestUndo:
    def test_undo_when_nothing_done(self, store_path: Path):
        store = TodoStore(store_path)
        store.add_todo("Open")
        assert store.undo_last_done() is False

    def test_undo_undoes_last_done_from_end(self, store_path: Path):
        store = TodoStore(store_path)
        a = store.add_todo("First")
        b = store.add_todo("Second")
        c = store.add_todo("Third")
        a.done = True
        c.done = True
        store.update_todo(a)
        store.update_todo(c)
        result = store.undo_last_done()
        assert result is True
        todos = store.get_todos()
        # Last done from end is c.
        assert todos[-1].done is False

    def test_undo_undoes_first_done_when_only_one(self, store_path: Path):
        store = TodoStore(store_path)
        a = store.add_todo("Only done")
        a.done = True
        store.update_todo(a)
        store.add_todo("Open")
        assert store.undo_last_done() is True
        assert store.get_todos()[0].done is False


# ---------------------------------------------------------------------------
# Long-term edge cases
# ---------------------------------------------------------------------------

class TestLongTerm:
    def test_promote_out_of_range_noop(self, store_path: Path):
        store = TodoStore(store_path)
        store.ensure_file()
        store.promote_long_term(99)  # out of range
        assert len(store.get_todos()) == 0

    def test_promote_negative_index_noop(self, store_path: Path):
        store = TodoStore(store_path)
        store.ensure_file()
        store.promote_long_term(-1)
        assert len(store.get_todos()) == 0

    def test_promote_updates_display_id(self, store_path: Path):
        store = TodoStore(store_path)
        store.add_long_term("Promote me")
        store.promote_long_term(0)
        assert store.data["display_id"] > 0

    def test_remove_last_item(self, store_path: Path):
        store = TodoStore(store_path)
        store.add_long_term("Only one")
        store.remove_long_term(0)
        assert len(store.get_long_term()) == 0

    def test_remove_out_of_range_noop(self, store_path: Path):
        store = TodoStore(store_path)
        store.ensure_file()
        store.remove_long_term(5)  # should not crash

    def test_remove_negative_noop(self, store_path: Path):
        store = TodoStore(store_path)
        store.ensure_file()
        store.remove_long_term(-1)  # should not crash

    def test_promote_empty_text_skipped(self, store_path: Path):
        store = TodoStore(store_path)
        store.data["long-term"] = [{"text": ""}]
        store.promote_long_term(0)
        assert len(store.get_todos()) == 0


# ---------------------------------------------------------------------------
# Display ID edge cases
# ---------------------------------------------------------------------------

class TestDisplayId:
    def test_delete_displayed_task_orphans_display_id(self, store_path: Path):
        store = TodoStore(store_path)
        a = store.add_todo("Displayed")
        store.add_todo("Other")
        assert store.data["display_id"] == a.id or store.data["display_id"] == 2
        store.delete_todo(store.data["display_id"])
        # display_id still points to deleted item — display layer handles fallback.
        # Just check the store doesn't crash.
        store.save()

    def test_set_display_id_saves(self, store_path: Path):
        store = TodoStore(store_path)
        store.add_todo("A")
        store.add_todo("B")
        store.set_display_id(2)
        assert store.data["display_id"] == 2


# ---------------------------------------------------------------------------
# Environment persistence
# ---------------------------------------------------------------------------

class TestEnvironmentPersistence:
    def test_environment_persists_and_reloads(self, store_path: Path):
        store = TodoStore(store_path)
        item = store.add_todo("Task with environment")
        item.environment = Environment(path="/tmp/clicktodo-env")
        store.update_todo(item)
        store.reload()
        todos = store.get_todos()
        assert len(todos) == 1
        assert todos[0].environment is not None
        assert todos[0].environment.path == "/tmp/clicktodo-env"


# Import TodoItem at module level
from clicktodo.models import TodoItem  # noqa: E402
