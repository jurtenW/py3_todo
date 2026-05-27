# Status Bar Adapter (py3status)

## Overview

The py3status adapter (`clicktodo/adapters/py3status_bar.py`) integrates clicktodo into the i3/py3status bar. It is loaded as a **py3status module** and runs continuously inside the py3status process, refreshing periodically to display task information.

## py3status Module Protocol

py3status loads modules by instantiating a class and calling its methods. The adapter defines the `Py3status` class with these conventions:

### Class-Level Configuration Attributes

py3status reads class-level attributes as configurable options. Users set these in their `i3status.conf`:

```python
class Py3status:
    data_path = ""              # Path to todos.json (empty = XDG default)
    format = "✅ {done}/{total} • {next}"  # Display format string
    max_width = 40              # Max chars for task text before truncation
    refresh_seconds = 5         # How often to refresh (seconds)
    ui_via_i3 = True            # Wrap UI launch with i3-msg exec
    ui_command = ""             # Custom UI command (empty = use default)
```

### Lifecycle Methods

#### post_config_hook()

Called once after py3status has applied configuration values from `i3status.conf`. This is where the store is initialized:

```python
def post_config_hook(self):
    path = self.data_path.strip() if self.data_path else str(default_data_path())
    self._store = TodoStore(resolve_path(path, module_root()))
    self._store.ensure_file()
```

#### clicktodo()

Called by py3status every `refresh_seconds`. Returns a dict with the formatted output:

```python
def clicktodo(self):
    self.store.reload()  # Pick up changes from Rofi UI
    done, total = display.todo_counts(self.store.data)
    text = display.next_label(self.store, self.max_width)
    return {
        "full_text": self.py3.safe_format(
            self.format,
            {"done": done, "total": total, "next": text},
        ),
        "cached_until": self.py3.time_in(self.refresh_seconds),
    }
```

The return dict must contain:
- **`full_text`**: The string to display in the bar.
- **`cached_until`**: A Unix timestamp after which py3status should call this method again.

The `self.py3` object is injected by py3status at runtime. It provides:
- `safe_format(fmt, ctx)` -- formats a string with placeholder substitution.
- `time_in(seconds)` -- returns `time.time() + seconds`.

## Mouse Click Handling

### on_click(event)

Called when the user clicks on the clicktodo module in the status bar. The `event` dict contains a `button` key:

| Button | Action | Implementation |
|---|---|---|
| **1** (Left) | Launch Rofi UI | `spawn_ui(via_i3=self.ui_via_i3, custom_command=self.ui_command)` |
| **2** (Middle) | Mark displayed task done | `display.mark_displayed_done(store)` |
| **3** (Right) | Open environment | Calls `launch_environment(env)` to open all items |
| **4** (Scroll Up) | Cycle to previous task | `display.cycle_display(store, -1)` |
| **5** (Scroll Down) | Cycle to next task | `display.cycle_display(store, 1)` |

**Button numbering** follows X11 convention:
- Button 1 = Left click
- Button 2 = Middle click (scroll wheel press)
- Button 3 = Right click
- Button 4 = Scroll wheel up
- Button 5 = Scroll wheel down

Before any action, `store.reload()` is called to pick up external changes (e.g., from the Rofi UI).

### Right Click (Open Environment)

```python
elif button == 3:
    raw_item = display.get_display_item(store)
    if raw_item is not None:
        todo = TodoItem.from_dict(raw_item)
        if todo.environment:
            launch_environment(todo.environment)
```

This opens all items in the todo's environment using their designated applications. `launch_environment()` iterates over `environment.opens`, and for each `OpenItem` calls `launch_open_item()` which dispatches to the appropriate application (Firefox, VS Code, Cursor, Okular, RemNote, etc.).

This only activates when:
1. There's a displayed item.
2. The todo has an environment with at least one `OpenItem`.
3. The designated application binary is in `$PATH`.

## Configuration in i3status.conf

Example configuration:

```
order += "clicktodo"

clicktodo {
    format = "✅ {done}/{total} • {next}"
    max_width = 40
    refresh_seconds = 5
    data_path = ""
    ui_via_i3 = true
}
```

When `data_path` is empty or whitespace-only, the store falls back to `default_data_path()` which resolves to `$XDG_DATA_HOME/clicktodo/todos.json` (typically `~/.local/share/clicktodo/todos.json`).

## Theory: The py3status Framework

**py3status** is an extension framework for i3status (the default i3 window manager status bar). It allows writing modules in Python that integrate with the status bar. Key concepts:

### Module Loading

py3status discovers modules through entry points defined in `pyproject.toml`:

```toml
[project.entry-points."py3status"]
clicktodo = "clicktodo.adapters.py3status_bar:Py3status"
```

This tells py3status: "When the user references `clicktodo` in their config, load the `Py3status` class from `clicktodo.adapters.py3status_bar`."

### The Caching Model

py3status uses a **pull model** with caching. Instead of the module pushing updates, py3status periodically calls the module's primary method. The `cached_until` timestamp tells py3status when to call again. This is more efficient than continuous polling.

```
py3status main loop:
    for each module:
        if current_time >= module.cached_until:
            result = module.clicktodo()
            module.cached_until = result["cached_until"]
            update_bar(result["full_text"])
    sleep(until_next_refresh)
```

### The self.py3 Object

py3status injects a helper object at `self.py3` that provides framework utilities. This object doesn't exist at module definition time -- it's added at runtime. That's why the `py3status_bar` module is excluded from mypy type checking:

```toml
[[tool.mypy.overrides]]
module = ["clicktodo.adapters.py3status_bar"]
ignore_errors = true  # py3status adds self.py3 at runtime
```

### Format Strings

py3status supports format strings with placeholders. The `safe_format` method substitutes placeholders from a context dict:

```python
format = "✅ {done}/{total} • {next}"
# becomes "✅ 3/7 • Finish report"
```

## Theory: Why Adapters Are Separate

The py3status adapter is an **entry point** -- it's the bridge between the py3status framework and the core clicktodo logic. It doesn't contain business logic; it delegates to:

- `display.py` for view logic (counts, cycling, truncation)
- `store.py` for persistence
- `launch.py` for UI spawning

This keeps the adapter thin and testable. The actual logic lives in modules that don't depend on py3status.
