# Data Model

## Overview

The data model in `clicktodo/models.py` defines the core domain objects, serialization format, and schema versioning for the todo list. This module is **stateless** -- it has no file I/O, no side effects, and no external dependencies beyond the Python standard library.

## Core Data Structures

### TodoItem

The primary domain object. Each task has:

```python
@dataclass
class TodoItem:
    id: int                     # Auto-incrementing unique identifier
    text: str                   # Task description
    done: bool = False          # Completion status
    date: str | None = None     # Optional deadline (format: DD.MM.YYYY)
    created_at: int = 0         # Unix timestamp of creation (currently unused in add_todo)
    environment: Environment | None = None  # Optional execution context
```

**Field Details:**

- **`id`**: A monotonically increasing integer. Assigned by `TodoStore.add_todo()` using the `seq` counter in the JSON state. IDs are never reused, even after deletion.
- **`text`**: Free-form text. Can be empty (though not recommended).
- **`done`**: Boolean. `False` = open/active, `True` = completed.
- **`date`**: Optional deadline string in `DD.MM.YYYY` format. When `None`, the UI displays `DO IT` as a placeholder, meaning "no deadline, do it now."
- **`created_at`**: Unix timestamp. Currently not set by `add_todo()`, but preserved during serialization roundtrips.
- **`environment`**: Optional `Environment` that associates the todo with a project directory and files to open.

### Environment

Holds a list of files/URLs/items to open. Since schema v3, the environment no longer stores a standalone `path` — the project directory is represented as the first `OpenItem` in the `opens` list.

```python
@dataclass
class Environment:
    opens: list[OpenItem] = field(default_factory=list)  # Files/URLs to open
```

### OpenItem

A file, URL, or path to open with a specific application:

```python
@dataclass
class OpenItem:
    path: str           # File path or URL
    app: AppLauncher    # Which application to use
```

### AppLauncher

An enumeration of preset applications:

```python
class AppLauncher(Enum):
    FIREFOX = "firefox"
    CODE = "code"
    CURSOR = "cursor"
    OKULAR = "okular"
    REMNOTE = "RemNote.AppImage"
```

The launcher provides intelligent path detection:

| Path Pattern | Launcher |
|---|---|
| `http://` or `https://` | Firefox |
| `.pdf` extension | Okular |
| `.html`, `.htm`, `.url` extensions | Firefox |
| Everything else | VS Code (default) |

## JSON Serialization

### TodoItem.to_dict()

Converts a `TodoItem` to a plain dict for JSON serialization:

```python
{
    "idx": 1,
    "text": "Finish report",
    "done": False,
    "date": "15.06.2026",
    "time": 0,
    "environment": {
        "opens": [
            {"path": "/home/user/project", "app": "code"},
            {"path": "/home/user/project/README.md", "app": "code"}
        ]
    }
}
```

The `environment` key is **omitted** entirely when `self.environment` is `None` or when `opens` is empty, keeping the JSON clean.

### TodoItem.from_dict()

Reconstructs a `TodoItem` from a raw dict (loaded from JSON). This is the **deserialization** function and is designed for **forward compatibility**:

- Missing keys default to sensible values (`idx=0`, `text=""`, `done=False`, etc.).
- Unknown keys (from future schema versions) are silently ignored.
- The `environment` block is parsed defensively: if `opens` is empty or missing, the environment is treated as `None`.
- Legacy `path` key (pre-v3) is automatically converted to an `OpenItem` for backward compatibility.
- `opens` entries with empty paths are skipped.

## State Schema

### The JSON Document

The entire todo list is stored as a single JSON object with this structure:

```json
{
    "version": 2,
    "todos": [...],
    "archived": [...],
    "long-term": [...],
    "display_id": 0,
    "seq": 0
}
```

| Key | Type | Purpose |
|---|---|---|
| `version` | `int` | Schema version (currently `3`). Used for migrations. |
| `todos` | `list[dict]` | Active task list (both open and done). |
| `archived` | `list[dict]` | Permanently archived tasks (moved out of active list). |
| `long-term` | `list[dict]` | Backlog/someday ideas. Each entry is `{"text": "..."}`. |
| `display_id` | `int` | The `idx` of the task currently shown in the status bar. |
| `seq` | `int` | Monotonic counter for generating new IDs. |

### default_state()

Returns a fresh, empty state dict:

```python
def default_state() -> dict[str, Any]:
    return {
        "version": SCHEMA_VERSION,  # 3
        "todos": [],
        "archived": [],
        "long-term": [],
        "display_id": 0,
        "seq": 0,
    }
```

This is used when the data file doesn't exist, is corrupted, or is empty.

### normalize_state()

Ensures any loaded state is valid and up-to-date. Steps:

1. Reads the `version` field (defaults to `0` if missing).
2. Runs migration functions sequentially from `current_version` to `SCHEMA_VERSION`.
3. Sets `version = SCHEMA_VERSION`.
4. Merges with `default_state()` to fill in any missing keys.
5. Ensures `todos`, `archived`, and `long-term` are non-null lists.
6. **Preserves extra keys** (like `clock`) that may be added by future versions.

### open_todos()

Helper that filters `todos` to return only those where `done` is falsy:

```python
def open_todos(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [t for t in data.get("todos", []) if not t.get("done")]
```

## Theory: Data Classes

A **dataclass** (`@dataclass`) in Python is a decorator that automatically generates special methods (`__init__`, `__repr__`, `__eq__`, etc.) based on the class's type-annotated fields. This eliminates boilerplate code.

Key features used in this project:

- **Immutable-by-convention**: The dataclasses are mutable (you can set `item.done = True`), but they are treated as value objects -- you modify them, then call `store.update_todo(item)` to persist the change.
- **`field(default_factory=list)`**: For mutable default values (like `opens`), you must use `field(default_factory=list)` instead of `opens: list = []`. This is because default values in Python class definitions are evaluated once at class creation time, meaning all instances would share the same list. `default_factory` creates a new list for each instance.
- **`|` Union Syntax** (Python 3.10+): `str | None` means "either a `str` or `None`", equivalent to `Optional[str]`.

## Theory: Enumerations

An **Enum** (`class AppLauncher(Enum)`) defines a fixed set of named constants. Benefits:

- **Type Safety**: You can't accidentally pass `"chrom"` (typo) instead of `AppLauncher.FIREFOX`.
- **Self-Documenting**: `AppLauncher.CODE` is more readable than the string `"code"`.
- **Iteration**: You can iterate over all values: `for launcher in AppLauncher: ...`.
