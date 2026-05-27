# Rofi UI Adapter

## Overview

The Rofi UI (`clicktodo/adapters/rofi/`) provides a full-featured, keyboard-driven interface for managing todos. It uses **Rofi** (or **dmenu** as fallback) as its display mechanism -- a fuzzy-finder/dropdown menu that runs on the X11 display server.

The Rofi UI has two components:

| File | Role |
|---|---|
| `ui.py` | Low-level communication with the `rofi -dmenu` subprocess. Defines the `UIBackend` Protocol. |
| `app.py` | High-level application logic: menu building, task CRUD, workflows. |

## UIBackend Protocol

The UI layer is abstracted behind a **Protocol** (a structural typing interface from `typing.Protocol`):

```python
class UIBackend(Protocol):
    def show_menu(self, prompt: str, options: list[str]) -> str | None:
        ...

    def ask_text(self, prompt: str, initial: str = "") -> str | None:
        ...
```

The Protocol defines a contract: any object that implements these two methods can serve as a UI backend. This enables:

- **RofiUI** -- Production backend using `rofi -dmenu`.
- **MockUI** -- Test backend that records calls and returns queued responses.
- **Future backends** -- wofi, fuzzel, bemenu, etc.

### Theory: Structural Typing vs Nominal Typing

Python's `Protocol` uses **structural typing** (also called "duck typing" or "structural subtyping"). Unlike nominal typing (where a class must explicitly `implements` or `extends` an interface), structural typing only requires that the object has the right methods with the right signatures.

This means you don't need to declare `class RofiUI(UIBackend)` -- the type checker verifies conformance by checking that `RofiUI` has `show_menu()` and `ask_text()` methods.

## RofiUI Implementation

```python
class RofiUI:
    def __init__(self) -> None:
        self.rofi_bin = shutil.which("rofi") or "dmenu"

    def show_menu(self, prompt: str, options: list[str]) -> str | None:
        text = "\n".join(options)
        cmd = [self.rofi_bin, "-dmenu", "-p", prompt, "-i"]
        result = subprocess.run(cmd, input=text, text=True, capture_output=True)
        return result.stdout.strip() or None

    def ask_text(self, prompt: str, initial: str = "") -> str | None:
        cmd = [self.rofi_bin, "-dmenu", "-p", prompt, "-lines", "0"]
        result = subprocess.run(cmd, input=initial, text=True, capture_output=True)
        return result.stdout.strip() or None
```

### How It Works

1. **`show_menu`**: Joins the options with newlines and pipes them into `rofi -dmenu`. Rofi displays a dropdown menu. The user selects an option (or presses Escape to cancel). The selected text is read from `stdout`.
2. **`ask_text`**: Similar, but with `-lines 0` to show a single-line text input mode. The `initial` parameter provides pre-filled text.

### Rofi Flags

| Flag | Purpose |
|---|---|
| `-dmenu` | Run in dmenu-compatible mode (text input + dropdown) |
| `-p PROMPT` | Set the prompt text displayed in Rofi |
| `-i` | Case-insensitive fuzzy matching |
| `-lines 0` | Show 0 result lines (text input mode only) |

### Fallback to dmenu

`shutil.which("rofi")` returns `None` if Rofi isn't installed. In that case, `"dmenu"` is used as the command string. dmenu accepts the same flags, so the interface is compatible.

## TodoApp -- Application Logic

### The Main Loop

```python
def run(self) -> None:
    while True:
        menu_map = self._build_main_menu_map()
        selection = self.ui.show_menu("Todos", list(menu_map.keys()))
        if not selection:
            break
        action = menu_map.get(selection)
        if action:
            action()
```

The main loop is a **state machine** driven by menus:

1. Build the menu (a mapping from display labels to callback functions).
2. Show the menu and wait for user selection.
3. If the user cancels (empty selection), exit.
4. Call the selected action.
5. Loop back to rebuild the menu (showing updated state).

### Main Menu Structure

```
Todos
├── + Add new…
├── [#1] [15.06.2026] Finish report
├── [#2] [DO IT]     Fix login bug
├── [DONE] Old task
├── ⋯ Long-term (3)
├── ⋯ Archived (5)
└── Archive finished tasks
```

- **Open tasks** are sorted by deadline (earliest first, `DO IT` items last).
- **Done tasks** appear after open tasks.
- **Long-term** and **Archived** are sub-menus.
- The count in parentheses updates dynamically.

### Task Action Menu

When a task is selected, an action menu appears:

```
Action: Finish report
├── Toggle Done
├── Display
├── Edit Text
├── Edit Date
├── Manage Open Items
├── Delete
├── Archive
├── Open Environment        (only if environment exists)
├── Clear Environment       (only if environment exists)
└── Back
```

### Archive Menu

```
Archived
├── [#4] Old completed task
├── [#5] Another done task
└── Back
```

Selecting an archived item shows: `Restore to todos`, `Delete permanently`, `Back`.

### Long-Term Menu

```
Long-term
├── + Add long-term…
├── 1. Learn Rust
├── 2. Write blog post
└── Back
```

Selecting an item shows: `Promote to active todo`, `Remove`, `Back`.

## Open Items Management

Instead of a single environment path, each todo can have multiple **OpenItems** — files, URLs, or directories to open with specific applications. The "Manage Open Items" menu provides:

```
Open Items
├── + Add Open Item
├── + Add from directory
├── 1. [code] /home/user/project
├── 2. [firefox] https://example.com
├── Remove 1. [code] /home/user/project
├── Remove 2. [firefox] https://example.com
└── Back
```

- **Add Open Item**: Prompt for a path/URL, then select an app from `AppLauncher`. The app is auto-suggested based on the path (e.g., `.pdf` → Okular, `https://` → Firefox).
- **Add from directory**: Prompt for a directory, then an app. All files in that directory are added as OpenItems with the selected app.
- **Remove**: Remove a specific OpenItem by its displayed index.

### Environment Path Resolution

When the user enters a path, it can be relative, absolute, a `~`-prefixed home path, or a URL:

```python
def _resolve_env_path(self, raw: str) -> str:
    s = raw.strip()
    if not s:
        return ""
    # Pass URLs through without filesystem resolution.
    if s.startswith(("http://", "https://")):
        return s
    p = Path(s).expanduser()
    if not p.is_absolute():
        p = self.store.filepath.parent / p
    return str(p.resolve(strict=False))
```

- Empty input is rejected.
- URLs (`http://`, `https://`) are returned unchanged.
- `~` is expanded to the home directory.
- Relative paths are resolved relative to the data file's directory.
- `strict=False` means the path is resolved even if it doesn't exist yet.

## Open Environment Integration

When the user selects "Open Environment", `launch.launch_environment()` is called. This iterates over all `OpenItem` entries and opens each with its designated application:

```python
if choice == "Open Environment":
    if item.environment:
        launch.launch_environment(item.environment)
```

Each `OpenItem` is dispatched to the correct binary (Firefox, VS Code, Cursor, Okular, RemNote) via `launch.launch_open_item()`. If the binary isn't on `$PATH`, the item is silently skipped.

## The --set-environment Flag

A special command-line flag that opens the "Manage Open Items" screen for the currently displayed task:

```python
if "--set-environment" in sys.argv:
    item = display.get_display_item(store)
    # ... ensure environment exists, then:
    app._manage_open_items(todo)
```

This can be bound to an i3 keybinding for quickly adding or managing open items without opening the full UI.

## Theory: Process Communication via stdin/stdout

Rofi and dmenu communicate with their caller through standard I/O:

```
┌──────────┐  stdin (options)   ┌────────┐
│  Python   │ ─────────────────► │  Rofi  │
│  (caller) │                    │ (dmenu)│
│           │ ◄───────────────── │        │
└──────────┘  stdout (selection) └────────┘
```

1. The caller pipes newline-separated options into Rofi's stdin.
2. Rofi displays the options in a dropdown menu.
3. When the user selects (or cancels), Rofi writes the selected text to stdout and exits.
4. The caller reads stdout to get the result.

This is a common pattern for dmenu-style applications. The entire interaction happens through file descriptors, not IPC sockets or network connections. It's simple, portable, and doesn't require any libraries.

## Theory: subprocess.run vs subprocess.Popen

The codebase uses both:

- **`subprocess.run()`** (in `RofiUI`): Waits for the process to complete and captures output. Used when you need the result (menu selection).
- **`subprocess.Popen()`** (in `launch.py`, VSCode launch): Spawns the process and returns immediately. Used for fire-and-forget operations where you don't need the output.

| Method | Blocks? | Returns | Use When |
|---|---|---|---|
| `subprocess.run()` | Yes | `CompletedProcess` with stdout/stderr | You need the output |
| `subprocess.Popen()` | No | `Popen` object | You want to detach |
