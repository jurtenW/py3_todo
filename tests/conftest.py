"""Shared pytest fixtures for the clicktodo test suite."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from clicktodo.models import default_state
from clicktodo.store import TodoStore

from tests.fixtures.data import (
    make_state,
    sample_done_todo,
    sample_long_term_entry,
    sample_open_todo,
    sample_todo_with_env,
)
from tests.mock.ui import MockUI


# ---------------------------------------------------------------------------
# Store fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def store_path(tmp_path: Path) -> Path:
    """Path to an empty todos.json inside a temp directory."""
    return tmp_path / "todos.json"


@pytest.fixture
def store(store_path: Path) -> TodoStore:
    """Empty TodoStore backed by tmp_path."""
    s = TodoStore(store_path)
    s.ensure_file()
    return s


@pytest.fixture
def sample_store(store_path: Path) -> TodoStore:
    """TodoStore pre-populated with open/done/env tasks."""
    s = TodoStore(store_path)
    s.data = make_state(
        todos=[sample_open_todo(1), sample_done_todo(2), sample_todo_with_env(3)],
        archived=[],
        long_term=[sample_long_term_entry()],
        display_id=1,
        seq=3,
    )
    s.save()
    return s


@pytest.fixture
def corrupted_file(tmp_path: Path) -> Path:
    """A todos.json containing invalid JSON."""
    fp = tmp_path / "todos.json"
    fp.write_text("{{not valid json}}", encoding="utf-8")
    return fp


@pytest.fixture
def empty_file(tmp_path: Path) -> Path:
    """A todos.json that is an empty file."""
    fp = tmp_path / "todos.json"
    fp.write_text("", encoding="utf-8")
    return fp


@pytest.fixture
def old_schema_file(tmp_path: Path) -> Path:
    """A todos.json with version 0 (pre-migration) schema (no ``version`` key)."""
    fp = tmp_path / "todos.json"
    state = {
        "todos": [{"idx": 1, "text": "Legacy task", "done": False}],
        "archived": [],
        "long-term": [],
        "display_id": 1,
        "seq": 1,
    }
    fp.write_text(
        "\n".join(str(state).replace("'", '"')),
        encoding="utf-8",
    )
    # Write proper JSON without version key
    import json
    fp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return fp


# ---------------------------------------------------------------------------
# UI fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_ui() -> MockUI:
    """Fresh MockUI instance."""
    return MockUI()


# ---------------------------------------------------------------------------
# Py3status mock
# ---------------------------------------------------------------------------

class Py3Mock:
    """Minimal mock of py3status's ``self.py3`` object."""

    def safe_format(self, fmt: str, ctx: Dict[str, Any]) -> str:
        """Simple format-string renderer."""
        return fmt.format(**ctx)

    def time_in(self, seconds: int) -> float:
        import time
        return time.time() + seconds


@pytest.fixture
def py3_mock() -> Py3Mock:
    return Py3Mock()


# ---------------------------------------------------------------------------
# Permission helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def read_only_dir(tmp_path: Path) -> Path:
    """Create a read-only directory inside tmp_path."""
    d = tmp_path / "readonly"
    d.mkdir()
    d.chmod(stat.S_IRUSR)
    return d


# ---------------------------------------------------------------------------
# Environment variable fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def no_xdg_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove XDG_DATA_HOME from the environment."""
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)


@pytest.fixture
def custom_xdg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set XDG_DATA_HOME to a temp directory."""
    xdg = tmp_path / "xdg_data"
    xdg.mkdir()
    monkeypatch.setenv("XDG_DATA_HOME", str(xdg))
    return xdg
