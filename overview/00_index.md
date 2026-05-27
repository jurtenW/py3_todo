# Clicktodo -- Complete Overview

This directory contains comprehensive documentation for the clicktodo application. Read the files in order for a complete understanding, or jump to the topic you need.

## Reading Order

| # | File | Topic | Read If You Want To |
|---|---|---|---|
| 1 | [01_architecture_overview.md](01_architecture_overview.md) | High-level architecture, module layout, data flow | Understand how everything fits together |
| 2 | [02_data_model.md](02_data_model.md) | TodoItem, Environment, JSON serialization, dataclasses | Understand the domain objects and data format |
| 3 | [03_persistent_storage.md](03_persistent_storage.md) | TodoStore, atomic writes, CRUD operations, archiving | Understand how data is saved and loaded |
| 4 | [04_status_bar_adapter.md](04_status_bar_adapter.md) | py3status integration, click handlers, lifecycle | Understand how the status bar works |
| 5 | [05_rofi_ui.md](05_rofi_ui.md) | RofiUI, TodoApp, menu building, UIBackend Protocol | Understand the Rofi interface |
| 6 | [06_ui_launch_system.md](06_ui_launch_system.md) | spawn_ui(), i3-msg wrapping, command building | Understand how the UI is launched |
| 7 | [07_display_logic.md](07_display_logic.md) | Task counting, cycling, truncation, self-healing | Understand bar display logic |
| 8 | [08_schema_versioning.md](08_schema_versioning.md) | Schema versions, migrations, forward compatibility | Understand how data format evolves |
| 9 | [09_path_resolution.md](09_path_resolution.md) | XDG paths, module root, relative/absolute paths | Understand file path handling |
| 10 | [10_notification_system.md](10_notification_system.md) | py3-cmd refresh, inter-process communication | Understand bar refresh mechanism |
| 11 | [11_testing_strategy.md](11_testing_strategy.md) | Test pyramid, fixtures, MockUI, edge cases | Understand the test suite |
| 12 | [12_ci_cd_pipeline.md](12_ci_cd_pipeline.md) | GitHub Actions, test matrix, quality gates | Understand the CI pipeline |
| 13 | [13_configuration.md](13_configuration.md) | py3status config, environment variables, pyproject.toml | Understand all configuration options |
| 14 | [14_python_concepts.md](14_python_concepts.md) | Dataclasses, enums, protocols, pathlib, subprocess | Learn the Python features used |
| 15 | [15_i3wm_ecosystem.md](15_i3wm_ecosystem.md) | i3, py3status, Rofi, dmenu protocol, X11 | Understand the i3 ecosystem |

## Quick Reference

### Core Concepts

- **TodoItem**: A task with id, text, done status, deadline, and optional environment.
- **TodoStore**: JSON file persistence with atomic writes.
- **py3status adapter**: Status bar integration with click handlers.
- **Rofi UI**: Full-featured menu-driven interface.
- **Environment**: Associates a todo with one or more files/URLs to open (via OpenItems).
- **Display cycling**: Scroll through tasks in the status bar.
- **Schema migrations**: Automatic data format upgrades.

### Key Files

| File | What It Does |
|---|---|
| `src/clicktodo/models.py` | Domain objects, serialization, schema |
| `src/clicktodo/store.py` | JSON persistence, CRUD operations |
| `src/clicktodo/display.py` | Bar display logic (counts, cycling) |
| `src/clicktodo/adapters/py3status_bar.py` | Status bar integration |
| `src/clicktodo/adapters/rofi/app.py` | Rofi UI application |
| `src/clicktodo/adapters/rofi/ui.py` | Rofi subprocess communication |
| `src/clicktodo/launch.py` | UI process spawning, app launcher dispatch |
| `src/clicktodo/notify.py` | Bar refresh notification |
| `src/clicktodo/paths.py` | Path resolution helpers |

### Data File

- **Location**: `$XDG_DATA_HOME/clicktodo/todos.json` (default: `~/.local/share/clicktodo/todos.json`)
- **Format**: JSON with `version`, `todos`, `archived`, `long-term`, `display_id`, `seq`

### Commands

- `clicktodo-ui` -- Launch the Rofi UI (installed console script)
- `clicktodo-ui --set-environment` -- Set environment for displayed task
- `py3-cmd refresh clicktodo` -- Tell py3status to refresh the module
