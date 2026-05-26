"""Integration tests for clicktodo.adapters.rofi.app."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from clicktodo.adapters.rofi.app import TodoApp
from clicktodo.store import TodoStore
from tests.mock.ui import MockUI


# ---------------------------------------------------------------------------
# TodoApp full workflow tests
# ---------------------------------------------------------------------------


class TestTodoAppWorkflow:
    def test_add_new_task(self, store_path: Path):
        store = TodoStore(store_path)
        store.ensure_file()
        ui = MockUI()
        ui.queue_menu_response("+ Add new…")
        ui.queue_menu_response(None)  # exit loop
        ui.queue_text_response("New task")
        ui.queue_text_response("25.12.2026")

        app = TodoApp(store, ui)
        app.run()

        todos = store.get_todos()
        assert len(todos) == 1
        assert todos[0].text == "New task"

    def test_cancel_add_returns_none_text(self, store_path: Path):
        """User cancels the text prompt for adding."""
        store = TodoStore(store_path)
        store.ensure_file()
        ui = MockUI()
        ui.queue_menu_response("+ Add new…")
        ui.queue_menu_response(None)  # exit
        ui.queue_text_response(None)  # cancel text input

        app = TodoApp(store, ui)
        app.run()

        assert len(store.get_todos()) == 0

    def test_exit_menu(self, store_path: Path):
        store = TodoStore(store_path)
        store.ensure_file()
        ui = MockUI()
        ui.queue_menu_response(None)  # immediately exit

        app = TodoApp(store, ui)
        app.run()

        # Should exit cleanly with no todos added.
        assert len(store.get_todos()) == 0

    def test_toggle_done_action(self, store_path: Path):
        store = TodoStore(store_path)
        store.add_todo("Toggle me")
        ui = MockUI()
        # Main menu: select the todo
        ui.queue_menu_response(f"[#{store.get_todos()[0].id}] [DO IT] Toggle me")
        # Action menu: toggle done
        ui.queue_menu_response("Toggle Done")
        # Main menu: exit
        ui.queue_menu_response(None)

        app = TodoApp(store, ui)
        app.run()

        assert store.get_todos()[0].done is True

    def test_back_from_item_actions(self, store_path: Path):
        """Choosing Back from item actions returns to main menu."""
        store = TodoStore(store_path)
        store.add_todo("Item")
        ui = MockUI()
        # Main menu: select the todo
        ui.queue_menu_response(f"[#{store.get_todos()[0].id}] [DO IT] Item")
        # Action menu: go back
        ui.queue_menu_response("Back")
        # Main menu: exit
        ui.queue_menu_response(None)

        app = TodoApp(store, ui)
        app.run()

    def test_archive_finished_tasks(self, store_path: Path):
        store = TodoStore(store_path)
        item = store.add_todo("To archive")
        item.done = True
        store.update_todo(item)
        ui = MockUI()
        ui.queue_menu_response("Archive finished tasks")
        ui.queue_menu_response(None)  # exit

        app = TodoApp(store, ui)
        app.run()

        assert len(store.get_todos()) == 0
        assert len(store.data["archived"]) == 1

    def test_empty_archive_menu(self, store_path: Path):
        store = TodoStore(store_path)
        store.ensure_file()
        ui = MockUI()
        ui.queue_menu_response(f"⋯ Archived ({len(store.data.get('archived', []))})")
        ui.queue_menu_response("Back")  # exit empty archive
        ui.queue_menu_response(None)  # exit main

        app = TodoApp(store, ui)
        app.run()

    def test_long_term_promote_workflow(self, store_path: Path):
        store = TodoStore(store_path)
        store.add_long_term("Promote me")
        ui = MockUI()
        ui.queue_menu_response("⋯ Long-term (1)")
        ui.queue_menu_response("1. Promote me")
        ui.queue_menu_response("Promote to active todo")
        ui.queue_menu_response(None)  # exit main

        app = TodoApp(store, ui)
        app.run()

        assert len(store.get_long_term()) == 0
        assert len(store.get_todos()) == 1
        assert store.get_todos()[0].text == "Promote me"

    def test_long_term_remove_workflow(self, store_path: Path):
        store = TodoStore(store_path)
        store.add_long_term("Remove me")
        ui = MockUI()
        ui.queue_menu_response("⋯ Long-term (1)")
        ui.queue_menu_response("1. Remove me")
        ui.queue_menu_response("Remove")
        ui.queue_menu_response(None)

        app = TodoApp(store, ui)
        app.run()

        assert len(store.get_long_term()) == 0

    def test_edit_text_action(self, store_path: Path):
        store = TodoStore(store_path)
        store.add_todo("Original")
        ui = MockUI()
        ui.queue_menu_response(f"[#{store.get_todos()[0].id}] [DO IT] Original")
        ui.queue_menu_response("Edit Text")
        ui.queue_text_response("Edited text")
        ui.queue_menu_response(None)

        app = TodoApp(store, ui)
        app.run()

        assert store.get_todos()[0].text == "Edited text"

    def test_delete_todo(self, store_path: Path):
        store = TodoStore(store_path)
        item = store.add_todo("Delete me")
        ui = MockUI()
        ui.queue_menu_response(f"[#{item.id}] [DO IT] Delete me")
        ui.queue_menu_response("Delete")
        ui.queue_menu_response(None)

        app = TodoApp(store, ui)
        app.run()

        assert len(store.get_todos()) == 0

    def test_environment_roundtrip(self, store_path: Path):
        store = TodoStore(store_path)
        store.add_todo("With env")
        ui = MockUI()
        # Main: select todo
        ui.queue_menu_response(f"[#{store.get_todos()[0].id}] [DO IT] With env")
        # Action: set environment
        ui.queue_menu_response("Set Environment")
        ui.queue_text_response("/tmp/test-env")
        # Main: exit
        ui.queue_menu_response(None)

        app = TodoApp(store, ui)
        app.run()

        todo = store.get_todos()[0]
        assert todo.environment is not None
        assert "/tmp/test-env" in todo.environment.path

    def test_clear_environment(self, store_path: Path):
        from clicktodo.models import Environment

        store = TodoStore(store_path)
        item = store.add_todo("Has env")
        item.environment = Environment(path="/old/path")
        store.update_todo(item)
        ui = MockUI()
        # Main: select todo (with env it has extra options)
        todo_label = f"[#{item.id}] [DO IT] Has env"
        ui.queue_menu_response(todo_label)
        # Action: clear environment
        ui.queue_menu_response("Clear Environment")
        # Main: exit
        ui.queue_menu_response(None)

        app = TodoApp(store, ui)
        app.run()

        assert store.get_todos()[0].environment is None

    def test_restore_archived_item(self, store_path: Path):
        store = TodoStore(store_path)
        item = store.add_todo("Will archive")
        store.archive_todo(item)
        ui = MockUI()
        ui.queue_menu_response(f"⋯ Archived (1)")
        ui.queue_menu_response(f"[#{item.id}] Will archive")
        ui.queue_menu_response("Restore to todos")
        ui.queue_menu_response(None)

        app = TodoApp(store, ui)
        app.run()

        assert len(store.get_todos()) == 1
        assert len(store.get_archived_items()) == 0
