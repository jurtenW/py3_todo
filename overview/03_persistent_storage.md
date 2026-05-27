# Persistent Storage

## Overview

The `TodoStore` class in `clicktodo/store.py` is the persistence layer. It wraps a single JSON file and provides CRUD (Create, Read, Update, Delete) operations for todos, archiving, long-term backlog management, and state restoration.

## TodoStore Class

### Initialization

```python
store = TodoStore(filepath: Path)
```

On initialization, the store loads the JSON file. If the file doesn't exist, is corrupted, or is empty, it falls back to `default_state()`.

```python
def _load(self) -> dict[str, Any]:
    if not self.filepath.exists():
        return default_state()
    try:
        raw = json.loads(self.filepath.read_text(encoding="utf-8"))
        return normalize_state(raw)
    except (json.JSONDecodeError, OSError):
        return default_state()
```

The `normalize_state()` call ensures schema migrations are applied and missing keys are filled in.

### ensure_file()

Creates the parent directory (if needed) and writes an initial default state if the file doesn't exist:

```python
def ensure_file(self) -> None:
    self.filepath.parent.mkdir(parents=True, exist_ok=True)
    if not self.filepath.exists():
        self.save()
```

This is called by the py3status adapter's `post_config_hook()` and by the Rofi UI's `main()`.

### save() -- Atomic Writes

The most critical method. Writes the entire state to disk using an **atomic write pattern**:

```python
def save(self, *, refresh_bar: bool = False, indent: bool = True) -> None:
    self.filepath.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = self.filepath.with_suffix(self.filepath.suffix + ".tmp")
    payload = json.dumps(self.data, ensure_ascii=False, indent=2 if indent else None)
    tmp_path.write_text(payload, encoding="utf-8")
    tmp_path.rename(self.filepath)
    if refresh_bar:
        refresh_status_bar()
```

**How atomic writes work:**

1. Write to a temporary file (`todos.json.tmp`).
2. Atomically rename the temp file to the target (`todos.json`).
3. On Unix, `rename()` is an atomic operation -- either the old or new file exists, never a partial write.

This prevents data corruption if the process crashes or the system loses power mid-write. Without this pattern, a crash during `write_text()` could leave a partially-written JSON file that fails to parse on the next load.

The `refresh_bar` parameter triggers a `py3-cmd refresh clicktodo` call to update the status bar.

### reload()

Re-reads the file from disk. Used by the py3status adapter before each click handler to pick up changes made by other processes (like the Rofi UI).

```python
def reload(self) -> None:
    self.data = self._load()
```

## CRUD Operations

### Add Todo

```python
def add_todo(self, text: str, date: str | None = None) -> TodoItem:
    new_id = self.data.get("seq", 0) + 1
    self.data["seq"] = new_id
    item = TodoItem(id=new_id, text=text, date=date)
    self.data["todos"].append(item.to_dict())
    self.data["display_id"] = new_id
    self.save(refresh_bar=True)
    return item
```

- Increments `seq` for a new unique ID.
- Appends the serialized dict to `todos`.
- Sets `display_id` to the new item (so the status bar shows it immediately).
- Returns the `TodoItem` object (not the raw dict).

### Update Todo

```python
def update_todo(self, item: TodoItem) -> None:
    for i, raw in enumerate(self.data["todos"]):
        if raw.get("idx") == item.id:
            self.data["todos"][i] = item.to_dict()
            break
    self.save(refresh_bar=True)
```

Finds the todo by `idx` and replaces it with the updated version. If the ID doesn't exist, it's a no-op (doesn't crash).

### Delete Todo

```python
def delete_todo(self, item_id: int) -> None:
    self.data["todos"] = [
        t for t in self.data["todos"] if t.get("idx") != item_id
    ]
    self.save(refresh_bar=True)
```

Filters out the todo. Note: this does NOT update `display_id` -- if the displayed task is deleted, the display layer handles the stale reference via fallback.

### Set Display ID

```python
def set_display_id(self, item_id: int) -> None:
    self.data["display_id"] = item_id
    self.save(refresh_bar=True)
```

Explicitly sets which task is shown in the status bar. Used by the Rofi UI's "Display" action.

### Mark Done / Undo

```python
def mark_done_by_idx(self, idx: int) -> None:
    for t in self.data["todos"]:
        if t.get("idx") == idx:
            t["done"] = True
            break
    self.save()

def undo_last_done(self) -> bool:
    for t in reversed(self.data["todos"]):
        if t.get("done"):
            t["done"] = False
            self.save()
            return True
    return False
```

`undo_last_done()` iterates from the end of the list (most recent first) and unmarks the first `done` item it finds. Returns `True` if something was undone, `False` if nothing was done.

## Archive Operations

The archive is a separate list that holds completed tasks moved out of the active list. Unlike `done=True` (which keeps the task in the active list), archiving removes it entirely from active view.

```python
def archive_todo(self, item: TodoItem) -> None:
    self.data["archived"].append(item.to_dict())
    self.data["todos"] = [
        t for t in self.data["todos"] if t.get("idx") != item.id
    ]
    self.save(refresh_bar=True)

def archive_finished_todos(self) -> None:
    for item in self.get_todos():
        if item.done:
            self.data["archived"].append(item.to_dict())
    self.data["todos"] = [t for t in self.data["todos"] if not t.get("done")]
    self.save(refresh_bar=True)
```

### Restore / Delete Archived

```python
def restore_archived(self, item_id: int) -> None:
    archived = self.data.get("archived", [])
    for i, raw in enumerate(archived):
        if raw.get("idx") == item_id:
            item = TodoItem.from_dict(raw)
            item.done = False  # Reset done status on restore
            self.data["todos"].append(item.to_dict())
            del archived[i]
            self.save(refresh_bar=True)
            return

def delete_archived(self, item_id: int) -> None:
    self.data["archived"] = [
        t for t in self.data.get("archived", []) if t.get("idx") != item_id
    ]
    self.save(refresh_bar=True)
```

## Long-Term Backlog

Long-term items are simple entries with just text -- no IDs, no done status, no deadlines:

```python
def get_long_term(self) -> list[dict[str, Any]]:
    return list(self.data.get("long-term") or [])

def add_long_term(self, text: str) -> None:
    self.data.setdefault("long-term", []).append({"text": text})
    self.save(refresh_bar=True)

def promote_long_term(self, index: int) -> None:
    lt = self.data.setdefault("long-term", [])
    if index < 0 or index >= len(lt):
        return
    entry = lt.pop(index)
    text = entry.get("text", "")
    if text:
        new_id = self.data.get("seq", 0) + 1
        self.data["seq"] = new_id
        item = TodoItem(id=new_id, text=text)
        self.data["todos"].append(item.to_dict())
        self.data["display_id"] = new_id
    self.save(refresh_bar=True)

def remove_long_term(self, index: int) -> None:
    lt = self.data.setdefault("long-term", [])
    if 0 <= index < len(lt):
        lt.pop(index)
        self.save(refresh_bar=True)
```

Long-term items are identified by their **list index** (0-based), not by an ID. This is different from todos, which use unique `idx` values. The trade-off: indices can shift when items are removed, but long-term operations always rebuild the menu from the current state, so stale indices are handled by bounds checking.

## Theory: Why Atomic Writes Matter

Without atomic writes, the save operation looks like this:

```python
# NON-ATOMIC (bad):
self.filepath.write_text(payload, encoding="utf-8")
```

If the process crashes after writing 50% of the file, the file is now corrupted. On the next load, `json.loads()` raises `JSONDecodeError`.

With atomic writes:

```python
# ATOMIC (good):
tmp_path.write_text(payload, encoding="utf-8")  # Write to temp
tmp_path.rename(self.filepath)                    # Atomic swap
```

The `rename()` system call on POSIX is atomic -- it's implemented as a metadata operation in the filesystem. Either the old file or the new file exists; there's no intermediate state where the file is half-written.

This pattern is used by databases, configuration managers, and any system where data integrity matters.

## Theory: Why Separate Store from Models

The store knows about persistence (file paths, JSON serialization, atomic writes). The models know about domain semantics (what a todo is, how to serialize a single item, schema migrations). By separating these:

1. **Models can be tested in isolation** without file system fixtures.
2. **Store can be replaced** (e.g., with a database backend) without changing the domain logic.
3. **Display logic** can work with raw dicts or TodoItem objects without knowing about file I/O.

This follows the **Repository Pattern** -- the store is a repository that abstracts away how data is persisted.
