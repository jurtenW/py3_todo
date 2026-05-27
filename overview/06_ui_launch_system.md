# UI Launch System

## Overview

The `launch.py` module handles three concerns:

1. **App launcher dispatch** -- opening files/URLs with the correct application (`launch_open_item()`, `launch_environment()`).
2. **Building the correct command** to invoke the UI (`ui_command()`).
3. **Wrapping with i3-msg** when running under i3 (`spawn_ui()`).

## App Launcher Dispatch

`launch.py` is responsible for opening files, URLs, and directories using the applications specified in `AppLauncher`. This is used by the status bar's right-click handler (`launch_environment()`) and the Rofi UI.

### launch_open_item()

```python
def launch_open_item(item: OpenItem) -> None:
    """Open a single OpenItem with its designated application."""
    cmd = _launch_command(item.app, item.path)
    if cmd is None:
        return
    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
```

### _launch_command()

Resolves the correct command-line arguments for each `AppLauncher`:

| AppLauncher | Command |
|---|---|
| `FIREFOX` | `firefox --new-tab <target>` |
| `CODE` | `code --reuse-window <target>` |
| `CURSOR` | `cursor <target>` |
| `OKULAR` | `okular <target>` |
| `REMNOTE` | `RemNote.AppImage <target>` |

Each launcher checks `shutil.which()` before dispatching. If the binary isn't on `$PATH`, `None` is returned and the item is silently skipped.

### launch_environment()

```python
def launch_environment(env: Environment) -> None:
    """Open every item in *env.opens*."""
    for item in env.opens:
        launch_open_item(item)
```

Iterates over all `OpenItem` entries in the environment and launches each one. This is called by the py3status adapter's right-click handler and the Rofi UI's "Open" action.

## ui_command() -- Building the Command

```python
def ui_command(data_path: Path, *, custom_command: str = "") -> list[str]:
    path = str(data_path.resolve())
    if custom_command.strip():
        parts = shlex.split(custom_command)
        return [*parts, path]
    ui_bin = shutil.which("clicktodo-ui")
    if ui_bin:
        return [ui_bin, path]
    return [sys.executable, "-m", "clicktodo.adapters.rofi.app", path]
```

### Resolution Order

1. **Custom command** (from py3status config `ui_command`): If the user has configured a custom UI command, use it. The data path is appended as the final argument.
2. **Installed entry point**: Check if `clicktodo-ui` is on `$PATH`. If so, use the full path.
3. **Module invocation**: Fall back to `python -m clicktodo.adapters.rofi.app`. This works even when the package isn't installed (e.g., during development).

### Shell Injection Prevention

Custom commands are parsed with `shlex.split()`, which properly handles quoting and prevents shell injection:

```python
# User config: ui_command = 'my-ui --foo'
# Result: ["my-ui", "--foo", "/path/to/todos.json"]

# Malicious input: ui_command = '"; rm -rf /" '
# shlex.split handles this safely - no shell is invoked
```

Without `shlex.split()`, a malicious or malformed config value could inject arbitrary commands. `shlex.split()` tokenizes the string according to shell quoting rules, but doesn't invoke a shell.

## spawn_ui() -- Spawning the Process

```python
def spawn_ui(data_path: Path | None = None, *, via_i3: bool = True, custom_command: str = "") -> None:
    path = data_path if data_path is not None else default_data_path()
    cmd = ui_command(path, custom_command=custom_command)

    if via_i3 and shutil.which("i3-msg"):
        argv = ["i3-msg", "-q", "exec", "--", *cmd]
        popen_kw: dict = {}
    else:
        argv = cmd
        popen_kw = {"start_new_session": True}

    # Debug logging or devnull
    if _debug_enabled():
        log_path = _launch_log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as log:
            log.write(f"spawn_ui argv={argv!r}\n")
        stdout_dest = None
        stderr_dest = None
    else:
        stdout_dest = subprocess.DEVNULL
        stderr_dest = subprocess.DEVNULL

    subprocess.Popen(argv, env=os.environ.copy(), stdout=stdout_dest, stderr=stderr_dest, **popen_kw)
```

### i3-msg Wrapper

When running under i3, the UI should be launched through `i3-msg exec`. This ensures:

- The window is managed by i3 properly (focused, placed in the correct workspace).
- The process is associated with the i3 session.
- Window rules and i3 configurations apply.

```bash
i3-msg -q exec -- clicktodo-ui /path/to/todos.json
```

The `-q` flag suppresses output from `i3-msg` itself.

When `i3-msg` isn't available (or `via_i3=False`), the UI is launched directly with `start_new_session=True`, which creates a new session so the process is detached from the parent.

### Environment Inheritance

`env=os.environ.copy()` passes the full environment to the child process. This is important because:

- The child needs `DISPLAY` to open a window.
- The child needs `XDG_DATA_HOME` to find configuration.
- VSCode (launched from within the UI) needs the environment to function.

### Debug Logging

When `CLICKTODO_DEBUG=1` is set in the environment:

```python
def _debug_enabled() -> bool:
    return bool(os.environ.get("CLICKTODO_DEBUG"))

def _launch_log_path() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".local" / "share"
    return base / "clicktodo" / "launch.log"
```

The log file records the exact argv passed to `subprocess.Popen()`. This helps debug issues where the UI doesn't launch or launches with wrong arguments.

## Theory: Process Management in Unix

### Process Groups and Sessions

When you spawn a process with `start_new_session=True`, the child gets a new **session** and **process group**. This means:

- The child doesn't inherit the parent's controlling terminal.
- Signals (like Ctrl+C) sent to the parent don't affect the child.
- The child continues running after the parent exits.

This is important for the UI launch: the status bar (py3status) shouldn't be affected if the user closes the Rofi UI, and the Rofi UI shouldn't die if py3status restarts.

### Why Not Use a Shell?

The code uses `subprocess.Popen(argv, ...)` with a list of arguments, NOT `subprocess.Popen("command arg1 arg2", shell=True)`. This is a security best practice:

- **No shell injection**: With `shell=True`, special characters in arguments can be interpreted as shell metacharacters.
- **Direct execution**: The executable is run directly, without spawning an intermediate `/bin/sh`.
- **Performance**: Slightly faster since no shell process is created.

### Why Use subprocess.Popen Instead of os.system?

| Approach | Safety | Output Capture | Process Control |
|---|---|---|---|
| `os.system()` | Shell injection risk | No | None |
| `subprocess.run()` | Safe (list args) | Yes | Blocks |
| `subprocess.Popen()` | Safe (list args) | Yes | Detached |

`subprocess.Popen()` is the right choice when you want to spawn a process and not wait for it.
