# Architecture Overview

## What Is Clicktodo?

Clicktodo is a **command-line task manager** designed for the **i3 window manager** ecosystem on Linux. It integrates a todo list directly into the **py3status bar** (the i3 status bar), allowing you to see and manage tasks without leaving your keyboard-driven workflow.

The application has two main entry points:

1. **py3status adapter** -- a module that runs inside the status bar, displaying the current task, progress count, and responding to mouse clicks.
2. **Rofi UI** -- a full-featured dmenu-based interface (launched from the status bar or from the command line) for managing tasks: adding, editing, archiving, and setting environments.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Interaction                      │
│  ┌──────────────────┐         ┌──────────────────────┐  │
│  │  py3status Bar   │         │    Rofi UI (dmenu)   │  │
│  │  (Adapter)       │         │    (clicktodo-ui)    │  │
│  └────────┬─────────┘         └──────────┬───────────┘  │
│           │                              │              │
│           │  spawn_ui()                  │              │
│           └──────────────────────────────┘              │
│                           │                             │
│           ┌───────────────┼───────────────┐             │
│           ▼               ▼               ▼             │
│  ┌────────────────┐ ┌────────┐ ┌────────────────┐      │
│  │   display.py   │ │models  │ │   notify.py    │      │
│  │  (View Logic)  │ │.py     │ │ (Bar Refresh)  │      │
│  └────────────────┘ └───┬────┘ └────────────────┘      │
│                         │                               │
│           ┌─────────────┼───────────────┐               │
│           ▼             ▼               ▼               │
│  ┌────────────────┐ ┌────────┐ ┌────────────────┐      │
│  │   store.py     │ │paths   │ │   launch.py    │      │
│  │  (Persistence) │ │.py     │ │  (UI Spawn)    │      │
│  └────────────────┘ └────────┘ └────────────────┘      │
│                           │                             │
│              todos.json (XDG_DATA_HOME)                 │
└─────────────────────────────────────────────────────────┘
```

## Source Directory Layout

```
src/clicktodo/
├── __init__.py                # Package init; re-exports core types
├── models.py                  # TodoItem, Environment, OpenItem, schema, migrations
├── store.py                   # TodoStore -- JSON persistence, CRUD operations
├── display.py                 # Status-bar display logic (counts, cycling, truncation)
├── paths.py                   # Path resolution (module root, XDG data paths)
├── notify.py                  # py3-cmd notification to refresh the bar
├── launch.py                  # Spawns the Rofi UI (with i3-msg wrapper)
└── adapters/
    ├── __init__.py
    ├── py3status_bar.py       # py3status module (status bar integration)
    └── rofi/
        ├── __init__.py
        ├── ui.py              # RofiUI / dmenu subprocess interaction
        └── app.py             # TodoApp -- main Rofi UI application logic

tests/
├── conftest.py                # Shared pytest fixtures
├── fixtures/data.py           # Factory functions for test data
├── mock/ui.py                 # MockUI -- scriptable mock for UIBackend
├── unit/                      # Unit tests for individual modules
└── integration/               # Integration / workflow tests

data/
└── todos.json                 # User data file (in-repo for development)
```

## Module Responsibilities

### Core Layer (Stateless Models)

| Module | Purpose |
|---|---|
| `models.py` | Defines `TodoItem`, `Environment`, `OpenItem` dataclasses. Handles JSON serialization (`to_dict`/`from_dict`). Manages schema versioning and data migrations. |

### Persistence Layer

| Module | Purpose |
|---|---|
| `store.py` | `TodoStore` class wraps a JSON file. Handles atomic writes, CRUD operations, archiving, long-term backlog, and undo. |
| `paths.py` | Resolves file paths: module root, XDG-compliant data directory, relative-to-absolute path resolution. |

### Presentation Layer

| Module | Purpose |
|---|---|
| `display.py` | View logic: counting done/open tasks, cycling the displayed task, truncating text for the bar, marking the displayed task done. |
| `notify.py` | Calls `py3-cmd refresh clicktodo` to tell the status bar to re-render after data changes. |
| `launch.py` | Constructs the command to spawn the Rofi UI. Wraps with `i3-msg exec` when running under i3. Debug logging support. |

### Adapters (Entry Points)

| Module | Purpose |
|---|---|
| `adapters/py3status_bar.py` | The py3status module. Displays task info in the bar. Handles mouse clicks (left=launch UI, middle=mark done, right=open VSCode, scroll=cycle). |
| `adapters/rofi/ui.py` | `RofiUI` class that communicates with `rofi -dmenu` (or `dmenu` as fallback) via subprocess. Defines the `UIBackend` Protocol. |
| `adapters/rofi/app.py` | `TodoApp` -- the main application loop for the Rofi UI. Menu building, task management workflows, environment settings. |

## Entry Points

The package installs two entry points (defined in `pyproject.toml`):

```toml
[project.scripts]
clicktodo-ui = "clicktodo.adapters.rofi.app:main"

[project.entry-points."py3status"]
clicktodo = "clicktodo.adapters.py3status_bar:Py3status"
```

- **`clicktodo-ui`** -- Installed as a console script. Invokes `main()` in `rofi/app.py`. Can be called from the command line, from the py3status adapter, or from i3 keybindings.
- **`clicktodo` (py3status entry point)** -- Loaded by py3status as a module. The `Py3status` class is instantiated and its methods are called by the py3status framework.

## Data Flow

```
User clicks on status bar
       │
       ▼
  py3status_bar.on_click()
       │
       ├── Left click (button 1) ──► spawn_ui() ──► Rofi UI opens
       │                                         │
       │                                         ▼
       │                                    TodoApp.run() loop
       │                                         │
       │                                         ▼
       │                                    TodoStore (save)
       │                                         │
       │                                         ▼
       │                                    refresh_status_bar()
       │
       ├── Middle click (button 2) ──► mark_displayed_done()
       │
       ├── Right click (button 3) ──► Open environment in VSCode
       │
       ├── Scroll up (button 4)  ──► cycle_display(-1)
       │
       └── Scroll down (button 5) ──► cycle_display(1)
```

## Design Principles

1. **Separation of Concerns** -- Models have no I/O. The store handles persistence. Display logic is independent of storage. Adapters are entry points only.
2. **Atomic Writes** -- The store writes to a `.tmp` file then renames, preventing data corruption on crashes.
3. **Schema Evolution** -- Data files are versioned. Migration functions registered via decorator upgrade old schemas automatically.
4. **Protocol-Based UI** -- The `UIBackend` Protocol defines the minimal interface for UI backends. Production uses RofiUI; tests use MockUI. This makes the app testable without a display server.
5. **XDG Compliance** -- Data is stored in `$XDG_DATA_HOME/clicktodo/todos.json` (defaults to `~/.local/share/clicktodo/todos.json`).
6. **Zero External Dependencies** -- The package has no runtime dependencies beyond Python 3.10+. All external tools (rofi, dmenu, i3-msg, py3-cmd, code) are optional and detected at runtime.
