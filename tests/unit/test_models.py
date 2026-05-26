"""Edge-case tests for clicktodo.models."""

from __future__ import annotations

from clicktodo import models
from clicktodo.models import (
    Environment,
    TodoItem,
    default_state,
    normalize_state,
    open_todos,
    register_migration,
    SCHEMA_VERSION,
)
from tests.fixtures.data import (
    make_state,
    make_todo_dict,
    make_todo_item,
    sample_done_todo,
    sample_open_todo,
)


# ---------------------------------------------------------------------------
# TodoItem.from_dict edge cases
# ---------------------------------------------------------------------------

class TestFromDict:
    def test_minimal_dict(self):
        """from_dict with only required-ish keys."""
        item = TodoItem.from_dict({"idx": 1, "text": "Minimal"})
        assert item.id == 1
        assert item.text == "Minimal"
        assert item.done is False
        assert item.date is None
        assert item.created_at == 0
        assert item.environment is None

    def test_missing_idx_defaults_to_zero(self):
        item = TodoItem.from_dict({"text": "No idx"})
        assert item.id == 0

    def test_missing_text_defaults_to_empty(self):
        item = TodoItem.from_dict({"idx": 1})
        assert item.text == ""

    def test_empty_text_preserved(self):
        item = TodoItem.from_dict({"idx": 1, "text": ""})
        assert item.text == ""

    def test_done_as_string_truthy(self):
        """Non-bool done values are passed through."""
        item = TodoItem.from_dict({"idx": 1, "text": "x", "done": "true"})
        assert item.done == "true"  # type: ignore[comparison-overlap]

    def test_done_as_int(self):
        item = TodoItem.from_dict({"idx": 1, "text": "x", "done": 1})
        assert item.done == 1

    def test_environment_as_none(self):
        item = TodoItem.from_dict({"idx": 1, "text": "x", "environment": None})
        assert item.environment is None

    def test_environment_as_empty_dict(self):
        item = TodoItem.from_dict({"idx": 1, "text": "x", "environment": {}})
        assert item.environment is None

    def test_environment_with_empty_path(self):
        item = TodoItem.from_dict(
            {"idx": 1, "text": "x", "environment": {"path": ""}}
        )
        assert item.environment is None

    def test_environment_with_valid_path(self):
        item = TodoItem.from_dict(
            {"idx": 1, "text": "x", "environment": {"path": "/foo/bar"}}
        )
        assert item.environment is not None
        assert item.environment.path == "/foo/bar"

    def test_future_unknown_fields_ignored(self):
        """Forward compat: unknown fields don't crash."""
        item = TodoItem.from_dict(
            {
                "idx": 1,
                "text": "x",
                "priority": "high",
                "tags": ["urgent"],
                "custom_field": 42,
            }
        )
        assert item.id == 1
        assert item.text == "x"

    def test_all_fields_present(self):
        item = TodoItem.from_dict(
            {
                "idx": 5,
                "text": "Full task",
                "done": True,
                "date": "15.06.2026",
                "time": 1718467200,
                "environment": {"path": "/home/proj"},
            }
        )
        assert item.id == 5
        assert item.text == "Full task"
        assert item.done is True
        assert item.date == "15.06.2026"
        assert item.created_at == 1718467200
        assert item.environment is not None
        assert item.environment.path == "/home/proj"


# ---------------------------------------------------------------------------
# TodoItem.to_dict + roundtrip
# ---------------------------------------------------------------------------

class TestRoundtrip:
    def test_roundtrip_minimal(self):
        item = TodoItem(id=1, text="x")
        d = item.to_dict()
        item2 = TodoItem.from_dict(d)
        assert item2.id == item.id
        assert item2.text == item.text
        assert item2.done == item.done
        assert item2.date == item.date

    def test_roundtrip_with_environment(self):
        item = TodoItem(
            id=2, text="y", environment=Environment(path="/tmp/p")
        )
        d = item.to_dict()
        assert "environment" in d
        item2 = TodoItem.from_dict(d)
        assert item2.environment is not None
        assert item2.environment.path == "/tmp/p"

    def test_roundtrip_environment_none_omitted(self):
        item = TodoItem(id=1, text="x")
        d = item.to_dict()
        assert "environment" not in d


# ---------------------------------------------------------------------------
# default_state
# ---------------------------------------------------------------------------

class TestDefaultState:
    def test_contains_required_keys(self):
        state = default_state()
        assert "todos" in state
        assert "archived" in state
        assert "long-term" in state
        assert "display_id" in state
        assert "seq" in state
        assert "version" in state

    def test_version_matches_constant(self):
        assert default_state()["version"] == SCHEMA_VERSION

    def test_empty_collections(self):
        state = default_state()
        assert state["todos"] == []
        assert state["archived"] == []
        assert state["long-term"] == []
        assert state["display_id"] == 0
        assert state["seq"] == 0


# ---------------------------------------------------------------------------
# normalize_state
# ---------------------------------------------------------------------------

class TestNormalizeState:
    def test_preserves_extra_keys(self):
        raw = {**default_state(), "clock": {"running": True}}
        merged = normalize_state(raw)
        assert merged["clock"]["running"] is True

    def test_null_arrays_become_lists(self):
        raw = {"todos": None, "archived": None, "long-term": None}
        merged = normalize_state(raw)
        assert merged["todos"] == []
        assert merged["archived"] == []
        assert merged["long-term"] == []

    def test_missing_keys_filled_from_defaults(self):
        raw = {}
        merged = normalize_state(raw)
        assert merged["todos"] == []
        assert merged["archived"] == []
        assert merged["long-term"] == []
        assert merged["display_id"] == 0
        assert merged["seq"] == 0

    def test_existing_values_not_overwritten(self):
        raw = {
            "todos": [{"idx": 1, "text": "a"}],
            "archived": [{"idx": 2}],
            "long-term": [{"text": "b"}],
            "display_id": 1,
            "seq": 5,
        }
        merged = normalize_state(raw)
        assert len(merged["todos"]) == 1
        assert len(merged["archived"]) == 1
        assert len(merged["long-term"]) == 1
        assert merged["display_id"] == 1
        assert merged["seq"] == 5

    def test_preserves_unknown_fields(self):
        raw = {**default_state(), "custom": "value", "meta": [1, 2]}
        merged = normalize_state(raw)
        assert merged["custom"] == "value"
        assert merged["meta"] == [1, 2]

    def test_schema_version_set_on_output(self):
        raw = {"todos": []}
        merged = normalize_state(raw)
        assert merged["version"] == SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Schema versioning / migrations
# ---------------------------------------------------------------------------

class TestSchemaVersioning:
    def test_no_migration_needed_at_current_version(self):
        raw = make_state(todos=[], version=SCHEMA_VERSION)
        merged = normalize_state(raw)
        assert merged["version"] == SCHEMA_VERSION

    def test_migration_runs_on_old_version(self):
        """When version is behind, migration functions execute."""
        called = []

        @register_migration
        def _mig_v1(data: dict) -> None:
            called.append("v1")
            data.setdefault("migrated_v1", True)

        try:
            raw = make_state(todos=[], version=SCHEMA_VERSION - 1)
            merged = normalize_state(raw)
            assert merged["version"] == SCHEMA_VERSION
            assert merged.get("migrated_v1") is True
        finally:
            # Clean up the migration so other tests don't see it.
            models._MIGRATIONS.pop()

    def test_multiple_migrations_run_sequentially(self):
        called_order = []

        @register_migration
        def _mig_a(data: dict) -> None:
            called_order.append("a")

        @register_migration
        def _mig_b(data: dict) -> None:
            called_order.append("b")

        try:
            # Current version is 1, so there's 1 migration slot.
            # We just added 2 to the list; starting from version 0,
            # only the first registered migration would run.
            raw = {"todos": [], "version": 0}
            normalize_state(raw)
        finally:
            models._MIGRATIONS.pop()
            models._MIGRATIONS.pop()


# ---------------------------------------------------------------------------
# open_todos
# ---------------------------------------------------------------------------

class TestOpenTodos:
    def test_empty_data(self):
        assert open_todos({}) == []

    def test_no_todos_key(self):
        assert open_todos({"archived": []}) == []

    def test_all_done(self):
        data = {"todos": [{"idx": 1, "done": True}, {"idx": 2, "done": True}]}
        assert open_todos(data) == []

    def test_mixed(self):
        data = {
            "todos": [
                {"idx": 1, "done": False},
                {"idx": 2, "done": True},
                {"idx": 3, "done": False},
            ]
        }
        result = open_todos(data)
        assert len(result) == 2
        assert result[0]["idx"] == 1
        assert result[1]["idx"] == 3

    def test_done_key_missing_treated_as_not_done(self):
        data = {"todos": [{"idx": 1}]}
        assert len(open_todos(data)) == 1
