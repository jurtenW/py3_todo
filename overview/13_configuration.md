# Configuration

## Overview

Clicktodo can be configured at two levels: the **py3status adapter** (via `i3status.conf`) and the **package/project** level (via `pyproject.toml`). There is no separate configuration file; all settings are passed through the py3status configuration or command-line arguments.

## py3status Configuration

Settings are defined as class-level attributes in `clicktodo/adapters/py3status_bar.py`. Users configure them in their `i3status.conf`:

### data_path

| Property | Value |
|---|---|
| Type | `str` |
| Default | `""` (empty = use XDG default) |
| Purpose | Path to the `todos.json` data file |

When empty or whitespace-only, falls back to `default_data_path()` which resolves to `$XDG_DATA_HOME/clicktodo/todos.json`.

Relative paths are resolved against the module root (repository root). Absolute paths and `~` expansion are supported.

### format

| Property | Value |
|---|---|
| Type | `str` |
| Default | `"✅ {done}/{total} • {next}"` |
| Purpose | Format string for the status bar display |

Available placeholders:

| Placeholder | Meaning | Example |
|---|---|---|
| `{done}` | Number of done tasks | `3` |
| `{total}` | Total number of tasks (done + open) | `7` |
| `{next}` | Text of the currently displayed task (truncated to `max_width`) | `Finish report` |

Custom examples:

```
format = "{done}/{total} {next}"           # Minimal
format = "📋 {next} ({done}/{total})"       # Task-focused
format = ""                                # Hide the module (only use clicks)
```

### max_width

| Property | Value |
|---|---|
| Type | `int` |
| Default | `40` |
| Purpose | Maximum character width for the task text before truncation |

Text longer than `max_width` is truncated and appended with `…`.

### refresh_seconds

| Property | Value |
|---|---|
| Type | `int` |
| Default | `5` |
| Purpose | How often (in seconds) py3status calls the display method |

Lower values mean more frequent updates but slightly more CPU usage. The notification system (`py3-cmd refresh`) provides immediate updates after data changes, so this primarily affects how quickly external changes (outside the Rofi UI) are picked up.

### ui_via_i3

| Property | Value |
|---|---|
| Type | `bool` |
| Default | `true` |
| Purpose | Whether to wrap the UI launch with `i3-msg exec` |

When `true` and `i3-msg` is available, the UI is launched via `i3-msg -q exec -- clicktodo-ui ...`. This ensures proper i3 window management.

Set to `false` when:
- Not using i3 (e.g., sway, hyprland, or another WM).
- Running without a window manager.

### ui_command

| Property | Value |
|---|---|
| Type | `str` |
| Default | `""` (empty = use default) |
| Purpose | Custom command to launch the UI |

When set, this command is used instead of the default `clicktodo-ui`. The data path is appended as the last argument.

Examples:

```
ui_command = ""                             # Use default (clicktodo-ui)
ui_command = "wofi --dmenu"                # Use wofi instead of rofi
ui_command = "fuzzel --dmenu"              # Use fuzzel
```

## Example i3status.conf

```
order += "clicktodo"

clicktodo {
    format = "✅ {done}/{total} • {next}"
    max_width = 40
    refresh_seconds = 5
    data_path = ""
    ui_via_i3 = true
    ui_command = ""
}
```

## Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `XDG_DATA_HOME` | Base directory for user data | `~/.local/share` |
| `CLICKTODO_DEBUG` | Enable debug logging for UI launches | Not set (disabled) |
| `DISPLAY` | X11 display server (needed for Rofi) | Set by X session |

When `CLICKTODO_DEBUG=1`, launch information is logged to `$XDG_DATA_HOME/clicktodo/launch.log`.

## pyproject.toml Configuration

The `pyproject.toml` file configures the build system, testing, linting, and type checking:

### Build System

```toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"
```

Uses **setuptools** as the build backend. No external build tools (Cython, CMake, etc.) are needed.

### Package Metadata

```toml
[project]
name = "clicktodo"
version = "0.2.0"
description = "i3 status bar todo list with Rofi UI"
requires-python = ">=3.10"
dependencies = []
```

- **Zero runtime dependencies**: The package only uses Python standard library modules.
- **Python 3.10+**: Uses the `|` union syntax (`str | None`) introduced in Python 3.10.

### Dev Dependencies

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "mypy>=1.0",
    "ruff>=0.1.0",
]
```

Installed with `pip install -e ".[dev]"`.

### Entry Points

```toml
[project.scripts]
clicktodo-ui = "clicktodo.adapters.rofi.app:main"

[project.entry-points."py3status"]
clicktodo = "clicktodo.adapters.py3status_bar:Py3status"
```

### Tool Configuration

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=clicktodo --cov-report=term-missing --cov-fail-under=80"

[tool.mypy]
packages = ["clicktodo"]
python_version = "3.10"
warn_return_any = true
disallow_untyped_defs = false

[tool.ruff]
src = ["src"]
target-version = "py310"
line-length = 99

[tool.ruff.lint]
select = ["E", "F", "W", "UP", "I"]
ignore = ["E501"]
```

## Data File Format

The `todos.json` file is a plain JSON document:

```json
{
    "version": 3,
    "todos": [
        {
            "idx": 1,
            "text": "Finish report",
            "done": false,
            "date": "15.06.2026",
            "time": 0,
            "environment": {
                "opens": [
                    {"path": "/home/user/project", "app": "code"}
                ]
            }
        }
    ],
    "archived": [],
    "long-term": [{"text": "Learn Rust"}],
    "display_id": 1,
    "seq": 1
}
```

The file can be edited manually, but changes should follow the schema. On next load, `normalize_state()` ensures the file is valid.

## Theory: Configuration as Code

py3status uses a **convention-over-configuration** approach:

1. **Defaults are sensible**: All options have reasonable defaults.
2. **Class attributes as config**: The framework reads class-level attributes as configuration options.
3. **post_config_hook lifecycle**: A hook method is called after configuration is applied, allowing initialization that depends on config values.

This pattern means the configuration schema is **self-documenting** -- you can see all available options and their defaults by reading the class definition.
