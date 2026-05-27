# Testing Strategy

## Overview

The test suite uses **pytest** and is organized into three tiers: unit tests, integration tests, and workflow tests. The goal is to achieve at least **80% code coverage** (enforced by CI).

## Test Directory Structure

```
tests/
├── conftest.py                # Shared pytest fixtures (store, mock_ui, py3_mock, etc.)
├── fixtures/
│   ├── __init__.py
│   └── data.py                # Factory functions for creating test data
├── mock/
│   ├── __init__.py
│   └── ui.py                  # MockUI -- scriptable mock for UIBackend
├── test_display.py            # Display logic tests (cycle, counts, fallback)
├── test_store.py              # Store CRUD tests, schema normalization
├── test_launch.py             # UI launch tests (command building, i3 wrapping)
├── unit/
│   ├── __init__.py
│   ├── test_models.py         # Edge cases: from_dict, roundtrip, state, migrations
│   ├── test_store.py          # Store edge cases: permissions, undo, display_id
│   ├── test_display.py        # Display edge cases: truncation, unicode, cycling
│   └── test_launch_paths_notify_ui.py  # Launch, paths, notify, protocol conformance
└── integration/
    ├── test_adapters.py       # Py3status adapter simulation
    └── test_full_workflow.py  # End-to-end Rofi UI workflows
```

## Test Tiers

### Unit Tests (`tests/unit/`)

Test individual modules in isolation, focusing on **edge cases**:

| File | Coverage |
|---|---|
| `test_models.py` | `from_dict` with missing keys, empty dicts, unknown fields, roundtrip serialization, `default_state()` validation, `normalize_state()` merging, migration registration |
| `test_store.py` | Missing file load, corrupted JSON, permission errors, noop on missing IDs, sequence integrity, undo edge cases, long-term bounds checking |
| `test_display.py` | Empty data, truncation boundaries, unicode/emoji, stale `display_id` fallback, cycle wrap-around |
| `test_launch_paths_notify_ui.py` | Custom commands, shell injection, i3-msg wrapping, XDG paths, py3-cmd missing |

### Integration Tests (`tests/integration/`)

Test components working together:

| File | Coverage |
|---|---|
| `test_adapters.py` | Py3status adapter lifecycle: config loading, format rendering, click handling, scroll cycling, whitespace-only paths |
| `test_full_workflow.py` | Rofi UI workflows: add task, toggle done, archive, long-term promote/remove, edit text, environment roundtrip |

### Root-Level Tests (`tests/*.py`)

Quick, focused tests for core functionality:

| File | Coverage |
|---|---|
| `test_display.py` | Cycle display wrapping, display_id fallback, todo counts |
| `test_store.py` | Default state keys, atomic save, add/archive, restore, undo, long-term promote |
| `test_launch.py` | UI command resolution, i3-msg wrapping, `--set-environment` flag |

## Fixtures and Factories

### conftest.py

Shared pytest fixtures that are automatically available to all tests:

| Fixture | Purpose |
|---|---|
| `store_path` | Path to an empty `todos.json` in a temp directory |
| `store` | Empty `TodoStore` backed by `tmp_path` |
| `sample_store` | Store pre-populated with open/done/env tasks |
| `corrupted_file` | A file with invalid JSON |
| `empty_file` | An empty file |
| `old_schema_file` | A v0 schema file (for migration testing) |
| `mock_ui` | Fresh `MockUI` instance |
| `py3_mock` | Minimal mock of `self.py3` |
| `read_only_dir` | A directory with read-only permissions |
| `no_xdg_env` | Removes `XDG_DATA_HOME` from environment |
| `custom_xdg` | Sets `XDG_DATA_HOME` to a temp directory |

### Factory Functions (`fixtures/data.py`)

Pure functions that create test data without side effects:

| Function | Returns |
|---|---|
| `make_todo_item(...)` | `TodoItem` with custom fields |
| `make_todo_dict(...)` | Raw dict (for JSON-level testing) |
| `make_state(...)` | Complete state dict with defaults |
| `sample_open_todo(idx)` | Open todo dict with date |
| `sample_done_todo(idx)` | Done todo dict |
| `sample_todo_with_env(idx)` | Todo with environment |
| `sample_long_term_entry(text)` | Long-term entry dict |

### MockUI (`mock/ui.py`)

A scriptable mock that implements the `UIBackend` protocol:

```python
mock = MockUI()
mock.queue_menu_response("Toggle Done")
mock.queue_text_response("My task")
mock.queue_menu_response(None)  # exit

app = TodoApp(store, mock)
app.run()

# Verify:
mock.assert_menu_shown("Action:")
mock.assert_asked_for("Edit")
```

The MockUI records all calls for assertion:
- `menu_calls` -- List of `(prompt, options)` tuples.
- `text_calls` -- List of `(prompt, initial)` tuples.

## Test Philosophy

### What We Test

1. **Edge cases**: Missing keys, empty lists, out-of-range indices, permission errors.
2. **Roundtrips**: Serialize to dict, then deserialize back. Verify data integrity.
3. **State transitions**: Add → archive → restore → verify `done=False`.
4. **Protocol conformance**: `RofiUI` and `MockUI` both implement `UIBackend`.
5. **Security**: Shell injection prevention in custom commands.

### What We Don't Test

1. **py3status internals**: The `self.py3` object is mocked. We don't test py3status itself.
2. **Rofi/dmenu behavior**: The actual subprocess communication is not tested (it requires a display server). We test the `TodoApp` logic with `MockUI`.
3. **i3 integration**: The i3-msg wrapping is tested via mocking `shutil.which` and `subprocess.Popen`.

## Running Tests

```bash
# All tests with coverage:
pytest

# Coverage threshold (80% minimum, enforced by --cov-fail-under=80):
pytest --cov=clicktodo --cov-report=term-missing --cov-fail-under=80

# Specific test file:
pytest tests/unit/test_models.py

# Specific test class:
pytest tests/unit/test_models.py::TestFromDict

# Verbose output:
pytest -v

# Skip coverage (faster):
pytest --no-cov
```

## Theory: Test Pyramid

The test suite follows the **Test Pyramid** pattern:

```
        /\
       /  \      E2E / Workflow Tests
      /____\        (few, slow, integration)
     /      \
    / UNIT   \      Unit Tests
   /__________\    (many, fast, isolated)
```

- **Unit tests** (base of the pyramid): Many, fast, isolated. Test individual functions and edge cases.
- **Integration tests** (middle): Test components working together. Moderate count.
- **Workflow tests** (top): End-to-end scenarios. Few, but catch integration bugs.

The ratio is roughly **70% unit, 20% integration, 10% workflow**. This ensures fast feedback during development while still catching integration issues.

## Theory: Why Use tmp_path?

Pytest's `tmp_path` fixture provides a unique temporary directory for each test. This ensures:

- **Isolation**: Tests don't interfere with each other.
- **Cleanup**: The temp directory is deleted after the test.
- **No state leakage**: Each test starts fresh.

The `store_path` and `store` fixtures use `tmp_path` to create temporary data files, so tests never touch the real `todos.json`.

## Theory: Mock vs Stub vs Fake

The test suite uses different types of test doubles:

| Type | Purpose | Example |
|---|---|---|
| **Mock** | Records interactions for verification | `MockUI` records `show_menu()` calls |
| **Stub** | Returns canned responses | `Py3Mock.safe_format()` returns formatted string |
| **Fake** | Lightweight implementation | `Py3Mock` implements the py3 interface without py3status |

The `MockUI` is both a **mock** (records calls for assertion) and a **stub** (returns queued responses). This combination is powerful for testing the TodoApp workflow.
