"""Integration tests for py3status adapter simulation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest

from clicktodo import display
from clicktodo.adapters.py3status_bar import Py3status
from clicktodo.models import TodoItem
from clicktodo.store import TodoStore


class Py3Mock:
    """Minimal mock of py3status's self.py3 object."""

    def safe_format(self, fmt: str, ctx: Dict[str, Any]) -> str:
        return fmt.format(**ctx)

    def time_in(self, seconds: int) -> float:
        import time
        return time.time() + seconds


class TestPy3statusAdapter:
    """Simulate the py3status adapter lifecycle."""

    def _create_adapter(self, store_path: Path, **kwargs) -> Py3status:
        """Create a Py3status instance with mocked self.py3."""
        adapter = Py3status()
        adapter.data_path = str(store_path)
        adapter.format = "✅ {done}/{total} • {next}"
        adapter.max_width = 40
        adapter.refresh_seconds = 5
        adapter.ui_via_i3 = False
        adapter.ui_command = ""
        adapter.py3 = Py3Mock()
        adapter.post_config_hook()
        return adapter

    def test_post_config_creates_file(self, tmp_path: Path):
        """post_config_hook should create the data file if missing."""
        fp = tmp_path / "todos.json"
        adapter = self._create_adapter(fp)
        assert fp.exists()

    def test_clicktodo_returns_formatted_string(self, tmp_path: Path):
        adapter = self._create_adapter(tmp_path / "todos.json")
        adapter.store.add_todo("Test task", date="01.01.2026")
        result = adapter.clicktodo()
        assert "full_text" in result
        assert "cached_until" in result
        assert "Test task" in result["full_text"]

    def test_clicktodo_with_empty_store(self, tmp_path: Path):
        adapter = self._create_adapter(tmp_path / "todos.json")
        result = adapter.clicktodo()
        assert "No Tasks" in result["full_text"]

    def test_clicktodo_counts_done_tasks(self, tmp_path: Path):
        adapter = self._create_adapter(tmp_path / "todos.json")
        item = adapter.store.add_todo("Task 1")
        adapter.store.add_todo("Task 2")
        item.done = True
        adapter.store.update_todo(item)
        result = adapter.clicktodo()
        assert "1/2" in result["full_text"]

    def test_custom_format(self, tmp_path: Path):
        adapter = Py3status()
        adapter.data_path = str(tmp_path / "todos.json")
        adapter.format = "{done} done of {total}"
        adapter.max_width = 40
        adapter.refresh_seconds = 5
        adapter.ui_via_i3 = False
        adapter.ui_command = ""
        adapter.py3 = Py3Mock()
        adapter.post_config_hook()
        adapter.store.add_todo("X")
        result = adapter.clicktodo()
        assert "0 done of 1" in result["full_text"]

    def test_empty_format_string(self, tmp_path: Path):
        adapter = self._create_adapter(tmp_path / "todos.json")
        adapter.format = ""
        result = adapter.clicktodo()
        assert result["full_text"] == ""

    def test_on_click_unknown_button_noop(self, tmp_path: Path):
        """Unknown button numbers should not crash."""
        adapter = self._create_adapter(tmp_path / "todos.json")
        adapter.on_click({"button": 99})

    def test_on_click_middle_click_marks_done(self, tmp_path: Path):
        adapter = self._create_adapter(tmp_path / "todos.json")
        adapter.store.add_todo("Mark me")
        adapter.on_click({"button": 2})
        todos = adapter.store.get_todos()
        assert todos[0].done is True

    def test_on_click_right_click_no_env(self, tmp_path: Path):
        """Right click with no environment should be a no-op."""
        adapter = self._create_adapter(tmp_path / "todos.json")
        adapter.store.add_todo("No env task")
        adapter.on_click({"button": 3})  # should not crash

    def test_on_click_scroll_cycles(self, tmp_path: Path):
        adapter = self._create_adapter(tmp_path / "todos.json")
        adapter.store.add_todo("First")
        adapter.store.add_todo("Second")
        # Set display_id to first task and persist to disk.
        first_id = adapter.store.get_todos()[0].id
        adapter.store.data["display_id"] = first_id
        adapter.store.save()
        initial_id = adapter.store.data["display_id"]

        # Scroll down (button 5) – on_click reloads from disk first.
        adapter.on_click({"button": 5})
        assert adapter.store.data["display_id"] != initial_id

    def test_whitespace_only_data_path(self, tmp_path: Path):
        """Whitespace-only data_path should fall back to default."""
        adapter = Py3status()
        adapter.data_path = "   "
        adapter.format = "{next}"
        adapter.max_width = 40
        adapter.refresh_seconds = 5
        adapter.ui_via_i3 = False
        adapter.ui_command = ""
        adapter.py3 = Py3Mock()
        # Should not crash; falls back to default_data_path()
        adapter.post_config_hook()

    def test_reload_on_click(self, tmp_path: Path):
        """on_click should reload the store to pick up external changes."""
        adapter = self._create_adapter(tmp_path / "todos.json")
        adapter.store.add_todo("Original")
        # Modify externally.
        adapter.store.data["todos"][0]["text"] = "Modified"
        adapter.store.save()
        # on_click reloads before acting.
        adapter.on_click({"button": 1})  # left click (UI launch, but we mock it)

    def test_zero_refresh_seconds(self, tmp_path: Path):
        """Zero refresh_seconds should not crash."""
        adapter = self._create_adapter(tmp_path / "todos.json")
        adapter.refresh_seconds = 0
        result = adapter.clicktodo()
        assert "full_text" in result

    def test_negative_refresh_seconds(self, tmp_path: Path):
        """Negative refresh_seconds should not crash."""
        adapter = self._create_adapter(tmp_path / "todos.json")
        adapter.refresh_seconds = -1
        result = adapter.clicktodo()
        assert "full_text" in result

    def test_on_click_right_click_with_opens(self, tmp_path: Path):
        """Right click with opens-based env calls launch_environment."""
        from clicktodo.models import Environment, OpenItem, AppLauncher

        adapter = self._create_adapter(tmp_path / "todos.json")
        item = adapter.store.add_todo("With opens")
        item.environment = Environment(
            opens=[OpenItem(path="/tmp/doc.pdf", app=AppLauncher.OKULAR)],
        )
        adapter.store.update_todo(item)

        from unittest.mock import patch
        with patch("clicktodo.adapters.py3status_bar.launch_environment") as mock_launch:
            adapter.on_click({"button": 3})
            mock_launch.assert_called_once()
