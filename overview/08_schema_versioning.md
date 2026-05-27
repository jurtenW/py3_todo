# Schema Versioning and Data Migrations

## Overview

The `models.py` module includes a schema versioning system that allows the data format to evolve over time without breaking existing data files. When the JSON layout changes, migration functions automatically upgrade old data to the current format.

## How It Works

### Schema Version Constant

```python
SCHEMA_VERSION: int = 3
```

This integer is incremented every time the JSON layout changes. The current version is `3`.

### Migration Registration

Migrations are registered using a decorator:

```python
_MIGRATIONS: list[Callable[[dict[str, Any]], None]] = []

def register_migration(fn) -> Callable:
    """Decorator to register a state-migration function."""
    _MIGRATIONS.append(fn)
    return fn

@register_migration
def _migration_v1_to_v2(data: dict[str, Any]) -> None:
    """Version 1 → 2: opens list is new; old todos just get default []."""
    pass


@register_migration
def _migration_v2_to_v3(data: dict[str, Any]) -> None:
    """Version 2 → 3: convert environment path into an OpenItem."""
    # ... converts environment.path to environment.opens[0] ...
```

Each migration function modifies the `data` dict **in-place**. The migration at index `i` upgrades from version `i` to version `i+1`.

### Migration Execution

When `normalize_state()` is called (during data load):

```python
def normalize_state(data: dict[str, Any]) -> dict[str, Any]:
    current_version = data.get("version", 0)

    # Run registered migrations sequentially from current_version → SCHEMA_VERSION.
    for migration_index in range(current_version, SCHEMA_VERSION):
        if migration_index < len(_MIGRATIONS):
            _MIGRATIONS[migration_index](data)

    data["version"] = SCHEMA_VERSION
    # ... merge with defaults ...
```

**Example**: If `SCHEMA_VERSION` is `3` and the data file has `version: 1`:

1. `migration_index = 1`: Runs `_MIGRATIONS[1]` (v1 → v2: opens list is new).
2. `migration_index = 2`: Runs `_MIGRATIONS[2]` (v2 → v3: environment.path → OpenItem).
3. Sets `data["version"] = 3`.

Each migration runs in sequence, transforming the data step by step.

## Why Migrations Modify In-Place

Migration functions receive the raw data dict and modify it directly (no return value). This is by design:

1. **Simple**: No need to construct a new dict; just add/remove/transform keys.
2. **Composable**: Each migration sees the output of the previous migration.
3. **Performance**: No extra allocation.

## Migration Indexing

The migration at `_MIGRATIONS[i]` upgrades from version `i` to `i+1`. This means:

| Index | Upgrades From | Upgrades To |
|---|---|---|
| 0 | Version 0 | Version 1 |
| 1 | Version 1 | Version 2 |
| 2 | Version 2 | Version 3 |

The loop `range(current_version, SCHEMA_VERSION)` generates indices that match this scheme. For example, with `current_version=1` and `SCHEMA_VERSION=3`:

```python
range(1, 3)  # yields [1, 2]
```

So migrations at index 1 and 2 are run.

## Writing a New Migration

When you change the data format:

1. **Increment `SCHEMA_VERSION`**:
   ```python
   SCHEMA_VERSION: int = 4  # was 3
   ```

2. **Register a migration** (at the new index, which is the old version):
   ```python
   @register_migration
   def _migration_v3_to_v4(data: dict[str, Any]) -> None:
       # Transform data from v3 format to v4 format
       for todo in data.get("todos", []):
           todo.setdefault("new_field", "default_value")
   ```

3. **Update `default_state()`** to include new keys:
   ```python
   def default_state() -> dict[str, Any]:
       return {
           "version": SCHEMA_VERSION,
           "todos": [],
           "new_key": [],  # New field
           # ... existing keys ...
       }
   ```

## Theory: Database Migration Patterns

This is the same pattern used by database migration tools like Alembic (SQLAlchemy), Django migrations, and Rails migrations:

1. **Versioned Schema**: Each schema change has a version number.
2. **Sequential Application**: Migrations are applied in order.
3. **Irreversibility**: Migrations go forward only (no built-in rollback).
4. **Idempotent State**: After all migrations run, the schema is at the latest version.

The key insight is that **migrations bridge the gap** between old and new data formats. Without migrations, upgrading the app would corrupt or lose existing data.

### Why Not Just Add Keys in normalize_state()?

You could add new keys directly in `normalize_state()`:

```python
data.setdefault("new_key", [])
```

This works for **additive changes** (adding new fields with defaults). But for **transformative changes** (renaming fields, changing data structures, splitting lists), you need the migration system.

The migration system provides a clean, documented place for transformative changes, making it clear what changed and why.

## Theory: Forward Compatibility

The `from_dict()` deserializer is designed for forward compatibility:

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> TodoItem:
    # ... reads known fields with .get() and defaults ...
    # Unknown fields are silently ignored
```

This means:
- A newer version of the app can read data written by an older version (via migrations).
- An older version of the app can read data written by a newer version (unknown fields are ignored).

This is called **backward-compatible schema evolution**. The complementary property (newer reads older) is **backward-compatible reading**.

## Theory: Decorator Pattern

The `@register_migration` decorator is an example of the **Decorator Pattern** used for registration:

```python
@register_migration
def _migration_v1_to_v2(data):
    pass
```

This is equivalent to:

```python
def _migration_v1_to_v2(data):
    pass
_migration_v1_to_v2 = register_migration(_migration_v1_to_v2)
```

The decorator:
1. Appends the function to `_MIGRATIONS`.
2. Returns the function unchanged (so the name still refers to the function).

This pattern is used for:
- Route registration in web frameworks (Flask `@app.route`).
- Signal handlers (Django `@receiver`).
- Plugin systems.
- Test fixtures.

The key benefit is that registration happens at **module load time**, so migrations are automatically discovered without explicit import or initialization code.
