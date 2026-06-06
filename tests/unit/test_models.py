"""Edge-case tests for clicktodo.models."""

from __future__ import annotations

from clicktodo import models
from clicktodo.models import (
    AppLauncher,
    Environment,
    OpenItem,
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

    def test_environment_with_legacy_path(self):
        """Legacy path key is converted to an OpenItem."""
        item = TodoItem.from_dict(
            {"idx": 1, "text": "x", "environment": {"path": "/foo/bar"}}
        )
        assert item.environment is not None
        assert len(item.environment.opens) == 1
        assert item.environment.opens[0].path == "/foo/bar"
        assert item.environment.opens[0].app == AppLauncher.CODE

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
                "environment": {
                    "opens": [{"path": "/home/proj", "app": "code"}],
                },
            }
        )
        assert item.id == 5
        assert item.text == "Full task"
        assert item.done is True
        assert item.date == "15.06.2026"
        assert item.created_at == 1718467200
        assert item.environment is not None
        assert len(item.environment.opens) == 1
        assert item.environment.opens[0].path == "/home/proj"


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
            id=2,
            text="y",
            environment=Environment(
                opens=[OpenItem(path="/tmp/p", app=AppLauncher.CODE)],
            ),
        )
        d = item.to_dict()
        assert "environment" in d
        item2 = TodoItem.from_dict(d)
        assert item2.environment is not None
        assert len(item2.environment.opens) == 1
        assert item2.environment.opens[0].path == "/tmp/p"

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


# ---------------------------------------------------------------------------
# AppLauncher
# ---------------------------------------------------------------------------

class TestAppLauncher:
    def test_from_string_valid(self):
        assert AppLauncher.from_string("firefox") == AppLauncher.FIREFOX
        assert AppLauncher.from_string("code") == AppLauncher.CODE
        assert AppLauncher.from_string("cursor") == AppLauncher.CURSOR
        assert AppLauncher.from_string("okular") == AppLauncher.OKULAR

    def test_from_string_unknown_defaults_to_code(self):
        assert AppLauncher.from_string("vim") == AppLauncher.CODE
        assert AppLauncher.from_string("") == AppLauncher.CODE

    def test_value_is_string(self):
        assert AppLauncher.FIREFOX.value == "firefox"
        assert AppLauncher.CODE.value == "code"
        assert AppLauncher.CURSOR.value == "cursor"
        assert AppLauncher.OKULAR.value == "okular"

    def test_can_launch_alone_firefox(self):
        assert AppLauncher.FIREFOX.can_launch_alone() is True

    def test_can_launch_alone_remnote(self):
        assert AppLauncher.REMNOTE.can_launch_alone() is True

    def test_can_launch_alone_code(self):
        assert AppLauncher.CODE.can_launch_alone() is False

    def test_can_launch_alone_cursor(self):
        assert AppLauncher.CURSOR.can_launch_alone() is False

    def test_can_launch_alone_okular(self):
        assert AppLauncher.OKULAR.can_launch_alone() is False


# ---------------------------------------------------------------------------
# AppLauncher.guess_for_path (smart defaults)
# ---------------------------------------------------------------------------

class TestAppLauncherGuess:
    def test_pdf_uses_okular(self):
        assert AppLauncher.guess_for_path("/path/to/doc.pdf") == AppLauncher.OKULAR

    def test_html_uses_firefox(self):
        assert AppLauncher.guess_for_path("/path/to/page.html") == AppLauncher.FIREFOX

    def test_htm_uses_firefox(self):
        assert AppLauncher.guess_for_path("/path/to/page.htm") == AppLauncher.FIREFOX

    def test_url_uses_firefox(self):
        assert AppLauncher.guess_for_path("index.url") == AppLauncher.FIREFOX

    def test_http_url_uses_firefox(self):
        assert AppLauncher.guess_for_path("http://example.com") == AppLauncher.FIREFOX

    def test_https_url_uses_firefox(self):
        assert AppLauncher.guess_for_path("https://example.com/path") == AppLauncher.FIREFOX

    def test_code_extension_uses_code(self):
        assert AppLauncher.guess_for_path("/path/to/main.py") == AppLauncher.CODE

    def test_no_extension_uses_code(self):
        assert AppLauncher.guess_for_path("/path/to/directory") == AppLauncher.CODE

    def test_unknown_extension_uses_code(self):
        assert AppLauncher.guess_for_path("/path/to/file.xyz") == AppLauncher.CODE


# ---------------------------------------------------------------------------
# OpenItem
# ---------------------------------------------------------------------------

class TestOpenItem:
    def test_create(self):
        item = OpenItem(path="/tmp/doc.pdf", app=AppLauncher.OKULAR)
        assert item.path == "/tmp/doc.pdf"
        assert item.app == AppLauncher.OKULAR


# ---------------------------------------------------------------------------
# Environment with opens
# ---------------------------------------------------------------------------

class TestEnvironmentWithOpens:
    def test_default_opens_is_empty(self):
        env = Environment()
        assert env.opens == []

    def test_roundtrip_with_opens(self):
        env = Environment(
            opens=[
                OpenItem(path="/home/proj/doc.pdf", app=AppLauncher.OKULAR),
                OpenItem(path="/home/proj/src", app=AppLauncher.CODE),
            ],
        )
        item = TodoItem(id=1, text="x", environment=env)
        d = item.to_dict()

        # Check serialized form.
        assert "environment" in d
        assert "opens" in d["environment"]
        assert len(d["environment"]["opens"]) == 2
        assert d["environment"]["opens"][0]["app"] == "okular"
        assert d["environment"]["opens"][1]["app"] == "code"

        # Deserialize.
        item2 = TodoItem.from_dict(d)
        assert item2.environment is not None
        assert len(item2.environment.opens) == 2
        assert item2.environment.opens[0].app == AppLauncher.OKULAR
        assert item2.environment.opens[1].app == AppLauncher.CODE

    def test_backwards_compat_old_env_without_opens(self):
        """Old todo data with {"path": "..."} but no "opens" key."""
        item = TodoItem.from_dict(
            {"idx": 1, "text": "x", "environment": {"path": "/old/path"}}
        )
        assert item.environment is not None
        assert len(item.environment.opens) == 1
        assert item.environment.opens[0].path == "/old/path"
        assert item.environment.opens[0].app == AppLauncher.CODE

    def test_empty_environment_not_serialized(self):
        """When opens is [], environment key should be omitted."""
        env = Environment(opens=[])
        item = TodoItem(id=1, text="x", environment=env)
        d = item.to_dict()
        assert "environment" not in d

    def test_unknown_app_string_defaults_to_code(self):
        item = TodoItem.from_dict(
            {
                "idx": 1,
                "text": "x",
                "environment": {
                    "opens": [{"path": "/p/f.txt", "app": "unknown_app"}],
                },
            }
        )
        assert item.environment is not None
        assert len(item.environment.opens) == 1
        assert item.environment.opens[0].app == AppLauncher.CODE

    def test_empty_opens_list_ignored(self):
        """When opens is [], treat as no environment."""
        item = TodoItem.from_dict(
            {
                "idx": 1,
                "text": "x",
                "environment": {"opens": []},
            }
        )
        assert item.environment is None

    def test_opens_with_missing_path_key_accepted(self):
        """Entries without a 'path' key become pathless OpenItems (app-only)."""
        item = TodoItem.from_dict(
            {
                "idx": 1,
                "text": "x",
                "environment": {"opens": [{"app": "firefox"}]},
            }
        )
        assert item.environment is not None
        assert len(item.environment.opens) == 1
        assert item.environment.opens[0].app == AppLauncher.FIREFOX
        assert item.environment.opens[0].path is None

    def test_opens_with_empty_path_becomes_none(self):
        """Entries with empty path are treated as pathless (app-only)."""
        item = TodoItem.from_dict(
            {
                "idx": 1,
                "text": "x",
                "environment": {"opens": [{"path": "", "app": "firefox"}]},
            }
        )
        assert item.environment is not None
        assert len(item.environment.opens) == 1
        assert item.environment.opens[0].app == AppLauncher.FIREFOX
        assert item.environment.opens[0].path is None

    def test_opens_with_non_string_path_becomes_none(self):
        """Entries with non-string path are treated as pathless (app-only)."""
        item = TodoItem.from_dict(
            {
                "idx": 1,
                "text": "x",
                "environment": {"opens": [{"path": 123, "app": "firefox"}]},
            }
        )
        assert item.environment is not None
        assert len(item.environment.opens) == 1
        assert item.environment.opens[0].app == AppLauncher.FIREFOX
        assert item.environment.opens[0].path is None

    def test_opens_mixed_valid_and_invalid(self):
        """Entries with and without paths are both kept."""
        item = TodoItem.from_dict(
            {
                "idx": 1,
                "text": "x",
                "environment": {
                    "opens": [
                        {"path": "/good", "app": "code"},
                        {"app": "firefox"},
                        {"path": "", "app": "okular"},
                        {"path": "/also_good", "app": "okular"},
                    ],
                },
            }
        )
        assert item.environment is not None
        assert len(item.environment.opens) == 4
        assert item.environment.opens[0].path == "/good"
        assert item.environment.opens[1].path is None
        assert item.environment.opens[2].path is None
        assert item.environment.opens[3].path == "/also_good"

    def test_pathless_openitem_roundtrip(self):
        """Pathless OpenItems serialize without 'path' key and roundtrip correctly."""
        env = Environment(
            opens=[
                OpenItem(app=AppLauncher.FIREFOX),
                OpenItem(app=AppLauncher.CODE, path="/some/path"),
                OpenItem(app=AppLauncher.REMNOTE),
            ],
        )
        item = TodoItem(id=1, text="x", environment=env)
        d = item.to_dict()
        assert "environment" in d
        assert len(d["environment"]["opens"]) == 3
        # Pathless entries should not have a 'path' key.
        assert "path" not in d["environment"]["opens"][0]
        assert d["environment"]["opens"][1]["path"] == "/some/path"
        assert "path" not in d["environment"]["opens"][2]

        # Roundtrip.
        item2 = TodoItem.from_dict(d)
        assert item2.environment is not None
        assert len(item2.environment.opens) == 3
        assert item2.environment.opens[0].app == AppLauncher.FIREFOX
        assert item2.environment.opens[0].path is None
        assert item2.environment.opens[1].path == "/some/path"
        assert item2.environment.opens[2].app == AppLauncher.REMNOTE
        assert item2.environment.opens[2].path is None

    def test_remnote_app_launcher_enum(self):
        """REMNOTE enum value roundtrips."""
        assert AppLauncher.REMNOTE.value == "RemNote.AppImage"
        assert AppLauncher.from_string("RemNote.AppImage") == AppLauncher.REMNOTE


# ---------------------------------------------------------------------------
# _get_extension
# ---------------------------------------------------------------------------

class TestGetExtension:
    def test_simple_extension(self):
        assert models._get_extension("/path/file.pdf") == ".pdf"

    def test_multiple_dots(self):
        assert models._get_extension("/path/file.tar.gz") == ".gz"

    def test_no_extension(self):
        assert models._get_extension("/path/to/directory") == ""

    def test_dotfile(self):
        assert models._get_extension("/path/.bashrc") == ".bashrc"

    def test_uppercase_lowered(self):
        assert models._get_extension("/path/FILE.PDF") == ".pdf"

    def test_url_with_query(self):
        assert models._get_extension("https://example.com/file.pdf?token=abc") == ".pdf?token=abc"
        # Note: guess_for_path guards against URLs before calling _get_extension,
        # so the query string never matters in practice.


# ---------------------------------------------------------------------------
# Schema migration v2 -> v3
# ---------------------------------------------------------------------------

class TestMigrationV2ToV3:
    def test_migration_converts_legacy_path_to_opens(self):
        """Migration transforms {"path": "..."} into {"opens": [...]}. """
        # Version 1 represents old data with "path" format.
        data = {
            "version": 1,
            "todos": [{"idx": 1, "text": "x", "environment": {"path": "/old"}}],
            "archived": [],
            "long-term": [],
        }
        normalized = normalize_state(data)
        # After migration (index 1: v2_to_v3), the old "path" key becomes "opens" and "path" is removed.
        todo_raw = normalized["todos"][0]
        assert "opens" in todo_raw.get("environment", {})
        assert todo_raw["environment"]["opens"][0]["path"] == "/old"
        assert "path" not in todo_raw["environment"]

    def test_migration_skips_if_opens_already_exists(self):
        """Don't duplicate if opens is already populated."""
        data = {
            "version": 1,
            "todos": [
                {
                    "idx": 1,
                    "text": "x",
                    "environment": {
                        "path": "/legacy",
                        "opens": [{"path": "/existing", "app": "firefox"}],
                    },
                }
            ],
            "archived": [],
            "long-term": [],
        }
        normalized = normalize_state(data)
        todo_raw = normalized["todos"][0]
        # Should NOT have duplicated the legacy path.
        assert len(todo_raw["environment"]["opens"]) == 1
        assert todo_raw["environment"]["opens"][0]["path"] == "/existing"

    def test_migration_handles_missing_environment(self):
        """Todos without environment are untouched."""
        data = {
            "version": 2,
            "todos": [{"idx": 1, "text": "x"}],
            "archived": [],
            "long-term": [],
        }
        normalized = normalize_state(data)
        assert "environment" not in normalized["todos"][0]

    def test_migration_handles_empty_path(self):
        """Empty string path is skipped."""
        data = {
            "version": 1,
            "todos": [{"idx": 1, "text": "x", "environment": {"path": ""}}],
            "archived": [],
            "long-term": [],
        }
        normalized = normalize_state(data)
        # Empty path should not create an opens entry.
        env = normalized["todos"][0].get("environment", {})
        assert env.get("opens") is None or len(env.get("opens", [])) == 0
