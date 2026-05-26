"""Edge-case tests for clicktodo.display."""

from __future__ import annotations

from pathlib import Path

from clicktodo import display
from clicktodo.store import TodoStore
from tests.fixtures.data import (
    make_state,
    sample_done_todo,
    sample_open_todo,
    sample_todo_with_env,
)


# ---------------------------------------------------------------------------
# todo_counts
# ---------------------------------------------------------------------------


class TestTodoCounts:
    def test_empty_data(self):
        done, total = display.todo_counts({"todos": []})
        assert done == 0
        assert total == 0

    def test_no_todos_key(self):
        done, total = display.todo_counts({})
        assert done == 0
        assert total == 0

    def test_all_open(self):
        data = {
            "todos": [
                {"idx": 1, "text": "A"},
                {"idx": 2, "text": "B"},
            ]
        }
        done, total = display.todo_counts(data)
        assert done == 0
        assert total == 2

    def test_all_done(self):
        data = {
            "todos": [
                {"idx": 1, "done": True},
                {"idx": 2, "done": True},
            ]
        }
        done, total = display.todo_counts(data)
        assert done == 2
        assert total == 2

    def test_mixed(self):
        data = {
            "todos": [
                {"idx": 1, "done": False},
                {"idx": 2, "done": True},
                {"idx": 3, "done": False},
            ]
        }
        done, total = display.todo_counts(data)
        assert done == 1
        assert total == 3

    def test_done_missing_treated_as_not_done(self):
        data = {"todos": [{"idx": 1}]}
        done, total = display.todo_counts(data)
        assert done == 0
        assert total == 1


# ---------------------------------------------------------------------------
# truncate_text
# ---------------------------------------------------------------------------


class TestTruncateText:
    def test_no_truncation_needed(self):
        assert display.truncate_text("short", 10) == "short"

    def test_exact_boundary(self):
        assert display.truncate_text("12345", 5) == "12345"

    def test_truncation_adds_ellipsis(self):
        result = display.truncate_text("Hello, World!", 5)
        assert result == "Hello…"

    def test_zero_max_width(self):
        result = display.truncate_text("anything", 0)
        assert result == "…"

    def test_negative_max_width(self):
        # Negative max_width means len(text) > -1 is always true for non-empty
        # strings, so it truncates to text[:-1] + ellipsis.
        result = display.truncate_text("anything", -1)
        assert result == "anythin…"

    def test_empty_string(self):
        assert display.truncate_text("", 5) == ""

    def test_unicode_multi_byte_chars(self):
        # "日本語" is 3 chars, each 3 bytes in UTF-8.
        result = display.truncate_text("日本語テスト", 3)
        assert result == "日本語…"

    def test_emoji(self):
        # len counts code points, not bytes.
        result = display.truncate_text("🎉🎊🎈", 2)
        assert result == "🎉🎊…"


# ---------------------------------------------------------------------------
# get_display_item
# ---------------------------------------------------------------------------


class TestGetDisplayItem:
    def test_returns_first_open_task(self, store_path: Path):
        store = TodoStore(store_path)
        store.data = make_state(
            todos=[sample_open_todo(1)],
            display_id=1,
            seq=1,
        )
        store.save()
        item = display.get_display_item(store)
        assert item is not None
        assert item["idx"] == 1

    def test_no_open_tasks_returns_none(self, store_path: Path):
        store = TodoStore(store_path)
        store.data = make_state(
            todos=[sample_done_todo(1)],
            display_id=1,
            seq=1,
        )
        store.save()
        item = display.get_display_item(store)
        assert item is None

    def test_no_todos_at_all_returns_none(self, store_path: Path):
        store = TodoStore(store_path)
        store.data = make_state(todos=[], display_id=0, seq=0)
        store.save()
        item = display.get_display_item(store)
        assert item is None

    def test_stale_display_id_falls_back(self, store_path: Path):
        store = TodoStore(store_path)
        store.data = make_state(
            todos=[sample_open_todo(1), sample_open_todo(2)],
            display_id=99999,  # stale
            seq=2,
        )
        store.save()
        item = display.get_display_item(store)
        assert item is not None
        # display_id should be corrected to first open task.
        assert store.data["display_id"] == 1

    def test_stale_display_id_after_delete(self, store_path: Path):
        """display_id points to a deleted todo."""
        store = TodoStore(store_path)
        store.add_todo("Keep", date="01.01.2026")
        store.add_todo("Delete", date="02.01.2026")
        store.delete_todo(2)
        store.data["display_id"] = 2  # stale
        item = display.get_display_item(store)
        assert item is not None
        assert item["idx"] == 1


# ---------------------------------------------------------------------------
# cycle_display
# ---------------------------------------------------------------------------


class TestCycleDisplay:
    def test_wraps_forward(self, store_path: Path):
        store = TodoStore(store_path)
        store.add_todo("A")
        store.add_todo("B")
        store.data["display_id"] = 1
        display.cycle_display(store, 1)
        assert store.data["display_id"] == 2
        display.cycle_display(store, 1)
        assert store.data["display_id"] == 1

    def test_wraps_backward(self, store_path: Path):
        store = TodoStore(store_path)
        store.add_todo("A")
        store.add_todo("B")
        store.data["display_id"] = 1
        display.cycle_display(store, -1)
        assert store.data["display_id"] == 2

    def test_single_task_stays(self, store_path: Path):
        store = TodoStore(store_path)
        store.add_todo("Only")
        store.data["display_id"] = 1
        display.cycle_display(store, 1)
        assert store.data["display_id"] == 1
        display.cycle_display(store, -1)
        assert store.data["display_id"] == 1

    def test_no_open_tasks_noop(self, store_path: Path):
        store = TodoStore(store_path)
        store.data = make_state(
            todos=[sample_done_todo(1)],
            display_id=1,
            seq=1,
        )
        store.save()
        display.cycle_display(store, 1)
        # Should not crash.

    def test_zero_open_tasks_noop(self, store_path: Path):
        store = TodoStore(store_path)
        store.data = make_state(todos=[], display_id=0, seq=0)
        store.save()
        display.cycle_display(store, 1)

    def test_skips_done_tasks(self, store_path: Path):
        store = TodoStore(store_path)
        store.data = make_state(
            todos=[
                sample_open_todo(1),
                sample_done_todo(2),
                sample_open_todo(3),
            ],
            display_id=1,
            seq=3,
        )
        store.save()
        display.cycle_display(store, 1)
        # Should skip done task #2 and land on #3.
        assert store.data["display_id"] == 3


# ---------------------------------------------------------------------------
# next_label
# ---------------------------------------------------------------------------


class TestNextLabel:
    def test_no_todos_returns_no_tasks(self, store_path: Path):
        store = TodoStore(store_path)
        store.data = make_state(todos=[], display_id=0, seq=0)
        store.save()
        label = display.next_label(store, max_width=40)
        assert label == "No Tasks"

    def test_all_done_returns_no_tasks(self, store_path: Path):
        store = TodoStore(store_path)
        store.data = make_state(
            todos=[sample_done_todo(1)],
            display_id=1,
            seq=1,
        )
        store.save()
        label = display.next_label(store, max_width=40)
        assert label == "No Tasks"

    def test_truncates_long_text(self, store_path: Path):
        store = TodoStore(store_path)
        store.data = make_state(
            todos=[{"idx": 1, "text": "A" * 50, "done": False}],
            display_id=1,
            seq=1,
        )
        store.save()
        label = display.next_label(store, max_width=10)
        assert len(label) <= 11  # 10 chars + ellipsis


# ---------------------------------------------------------------------------
# mark_displayed_done
# ---------------------------------------------------------------------------


class TestMarkDisplayedDone:
    def test_marks_task_done(self, store_path: Path):
        store = TodoStore(store_path)
        store.data = make_state(
            todos=[sample_open_todo(1)],
            display_id=1,
            seq=1,
        )
        store.save()
        result = display.mark_displayed_done(store)
        assert result is True
        todos = store.get_todos()
        assert todos[0].done is True

    def test_no_display_item_returns_false(self, store_path: Path):
        store = TodoStore(store_path)
        store.data = make_state(todos=[], display_id=0, seq=0)
        store.save()
        result = display.mark_displayed_done(store)
        assert result is False

    def test_all_done_returns_false(self, store_path: Path):
        store = TodoStore(store_path)
        store.data = make_state(
            todos=[sample_done_todo(1)],
            display_id=1,
            seq=1,
        )
        store.save()
        result = display.mark_displayed_done(store)
        assert result is False
