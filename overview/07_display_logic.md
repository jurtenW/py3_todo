# Display Logic

## Overview

The `display.py` module contains all the **view logic** for the status bar -- the code that decides what to show, how to count tasks, and how to navigate between them. It has no file I/O of its own; it operates on `TodoStore` objects and raw data dicts.

## Functions

### todo_counts()

```python
def todo_counts(data: dict[str, Any]) -> tuple[int, int]:
    todos = data.get("todos", [])
    done = sum(1 for t in todos if t.get("done"))
    return done, len(todos)
```

Returns `(done_count, total_count)`. The status bar format string uses these as `{done}` and `{total}`.

### truncate_text()

```python
def truncate_text(text: str, max_width: int) -> str:
    if len(text) > max_width:
        return text[:max_width] + "…"
    return text
```

Truncates text to `max_width` characters and appends an ellipsis (`…`). This prevents long task descriptions from overflowing the status bar.

**Note**: Truncation is by **character count** (Python's `len()`), not by byte count or display width. This means:
- Multi-byte Unicode characters (like `日`) count as 1 character.
- Emoji count as 1 character.
- Full-width characters may visually take more space than ASCII in monospaced fonts.

### get_display_item() -- Resolving the Displayed Task

```python
def get_display_item(store: TodoStore) -> dict[str, Any] | None:
    data = store.data
    display_id = data.get("display_id", 0)
    opens = open_todos(data)
    if not opens:
        return None

    for t in opens:
        if t.get("idx") == display_id:
            return t

    # Stale display_id -- fix it
    data["display_id"] = opens[0].get("idx")
    store.save()
    return opens[0]
```

This resolves the task currently shown in the bar:

1. Look up the task by `display_id`.
2. If not found (stale -- the task was deleted or archived), fall back to the first open task.
3. **Self-healing**: The stale `display_id` is corrected in the store and saved, so the next read is correct.

This is an example of **defensive programming** -- the function doesn't crash when the state is inconsistent; it repairs the state and continues.

### cycle_display() -- Rotating Among Tasks

```python
def cycle_display(store: TodoStore, direction: int) -> None:
    data = store.data
    opens = open_todos(data)
    if not opens:
        return

    current_id = data.get("display_id")
    current_idx = 0
    for i, t in enumerate(opens):
        if t.get("idx") == current_id:
            current_idx = i
            break

    new_idx = (current_idx + direction) % len(opens)
    data["display_id"] = opens[new_idx]["idx"]
    store.save()
```

Cycles through open (not-done) tasks. The `direction` parameter:
- `1` = next task (scroll wheel down)
- `-1` = previous task (scroll wheel up)

Uses **modular arithmetic** for wrapping: `(current_idx + direction) % len(opens)`. This means:
- Forward: `0 → 1 → 2 → 0 → ...`
- Backward: `0 → -1 ≡ 2 (mod 3) → 1 → 0 → ...`

Python's `%` operator always returns a non-negative result for positive modulus, so `(-1) % 3 == 2`, which is the correct wrap-around behavior.

### next_label() -- Building the Status Bar Text

```python
def next_label(store: TodoStore, max_width: int) -> str:
    item = get_display_item(store)
    if not item:
        return "No Tasks"
    return truncate_text(item.get("text", ""), max_width)
```

Returns the text to display in the status bar. If there are no open tasks, returns `"No Tasks"`.

### mark_displayed_done()

```python
def mark_displayed_done(store: TodoStore) -> bool:
    item = get_display_item(store)
    if not item:
        return False
    store.mark_done_by_idx(item["idx"])
    return True
```

Marks the currently displayed task as done. Used by the middle-click handler in the py3status adapter.

## Theory: Separation of View and Model

The display module follows the **Model-View-Controller** principle:

- **Model**: `TodoStore` and `TodoItem` -- the data and business logic.
- **View**: `display.py` -- formatting, truncation, and selection logic.
- **Controller**: `py3status_bar.py` and `TodoApp` -- event handlers that connect user actions to model mutations.

The display module:
- Reads from the store (but doesn't know how the store persists data).
- Doesn't handle user input directly (that's the adapter's job).
- Doesn't format for a specific UI (it returns plain strings).

This makes the display logic independently testable. You can test `truncate_text()` without a store, and `get_display_item()` with any store fixture.

## Theory: Self-Healing State

The `get_display_item()` function demonstrates **self-healing state**. Instead of crashing when `display_id` references a deleted task, it:

1. Detects the inconsistency.
2. Corrects the state.
3. Persists the correction.
4. Returns a valid result.

This pattern is important for robust software. Instead of assuming the state is always consistent, the code checks and repairs. This is especially important for state that persists across process boundaries (the status bar and Rofi UI are separate processes).
