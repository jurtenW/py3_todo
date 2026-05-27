# i3 Window Manager Ecosystem

## Overview

Clicktodo is designed for the **i3 window manager** ecosystem on Linux. Understanding this ecosystem is essential for understanding how clicktodo fits into the broader workflow.

## i3 Window Manager

**i3** is a tiling window manager for X11. Key characteristics:

- **Tiling**: Windows are arranged automatically in a tree structure (no overlapping).
- **Keyboard-driven**: Almost everything can be done with keyboard shortcuts.
- **Status bar**: i3status (or py3status) provides a customizable status bar at the top/bottom of the screen.
- **Configuration**: Plain text config file (`~/.config/i3/config`).

i3 is popular among developers because it minimizes mouse usage and maximizes screen real estate. Clicktodo fits this philosophy by providing a keyboard-driven task manager that integrates into the status bar.

## i3status

**i3status** is the default status bar for i3. It displays system information (time, battery, network, etc.) in a configurable format. Configuration is in `~/.config/i3status/config` or `~/.config/i3status/i3status.conf`.

### Limitations of i3status

- Written in C -- difficult to extend.
- Fixed set of modules (can't add custom Python logic).
- No click handlers for custom modules.

This is where **py3status** comes in.

## py3status

**py3status** is an extension framework for i3status. It:

1. Loads and runs i3status (as a subprocess).
2. Extends the output with Python modules.
3. Adds click handling, color customization, and more.

### How py3status Loads Modules

py3status discovers modules through Python **entry points**. When you install a package with:

```toml
[project.entry-points."py3status"]
clicktodo = "clicktodo.adapters.py3status_bar:Py3status"
```

py3status can load `clicktodo` from the user's `i3status.conf`:

```
order += "clicktodo"
clicktodo {
    format = "✅ {done}/{total} • {next}"
}
```

### The Module Lifecycle

```
py3status starts
    │
    ▼
Discover entry points (from installed packages)
    │
    ▼
Parse i3status.conf
    │
    ▼
For each module in `order`:
    │
    ├── Instantiate the class (e.g., Py3status())
    │
    ├── Apply configuration from config file
    │       (sets class attributes like format, max_width, etc.)
    │
    ├── Call post_config_hook()
    │       (module can now initialize with config values)
    │
    └── Enter refresh loop:
            │
            ├── Wait until cached_until
            │
            ├── Call the primary method (e.g., clicktodo())
            │
            ├── Update the bar with full_text
            │
            └── Loop
```

### Click Handling

When the user clicks on a module, py3status calls `on_click(event)`:

```python
def on_click(self, event):
    button = event["button"]  # 1=left, 2=middle, 3=right, 4=scroll_up, 5=scroll_down
    ...
```

This is how clicktodo handles left-click (open UI), middle-click (mark done), right-click (open VSCode), and scroll (cycle tasks).

## Rofi

**Rofi** is a window switcher, application launcher, and dmenu replacement for X11. Key features:

- **Fuzzy matching**: Type part of a name, Rofi finds matches.
- **Modes**: Window switching, application launching, dmenu mode, run mode, ssh mode.
- **Customizable**: Themes, keybindings, modes.
- **dmenu-compatible**: Accepts input on stdin, outputs selection on stdout.

Clicktodo uses Rofi in **dmenu mode** (`rofi -dmenu`):

```bash
echo -e "Option 1\nOption 2\nOption 3" | rofi -dmenu -p "Select"
```

### dmenu Protocol

The dmenu protocol is a simple IPC mechanism:

1. **Input**: Newline-separated options piped to stdin.
2. **Output**: Selected option written to stdout.
3. **Cancel**: Empty output (or exit code != 0) means the user cancelled.

This protocol is implemented by dmenu, Rofi, wofi, fuzzel, bemenu, and others. It's the standard way to do dropdown menus in keyboard-driven workflows.

### Rofi vs dmenu

| Feature | dmenu | Rofi |
|---|---|---|
| Fuzzy matching | No | Yes |
| Theming | Limited (X resources) | Extensive (rasi files) |
| Multiple modes | No | Yes (window, run, ssh, dmenu) |
| Keyboard shortcuts | Minimal | Extensive |
| Performance | Fast | Slightly slower |

Clicktodo prefers Rofi but falls back to dmenu for compatibility.

## i3-msg

**i3-msg** is the command-line interface for communicating with the i3 window manager. It sends commands to the running i3 instance via a Unix domain socket.

Clicktodo uses `i3-msg exec` to launch the Rofi UI:

```bash
i3-msg -q exec -- clicktodo-ui /path/to/todos.json
```

### Why Use i3-msg exec?

When a process is launched through `i3-msg exec`:

1. i3 manages the window (focuses it, places it in the current workspace).
2. i3 applies window rules (floating, size, position).
3. The process is associated with the i3 session.

Without `i3-msg exec`, the window might open unfocused, in the wrong workspace, or without i3 rules applied.

### Alternatives to i3-msg

| Window Manager | IPC Command |
|---|---|
| i3 | `i3-msg exec -- command` |
| sway (Wayland) | `swaymsg exec command` |
| hyprland (Wayland) | `hyprctl dispatch exec command` |
| No WM | Direct process spawn |

Clicktodo detects whether `i3-msg` is available and falls back to direct spawning when it's not.

## X11 Display Server

Rofi and dmenu require an X11 display server. They communicate with the X server to:

1. Create windows.
2. Handle keyboard input.
3. Render text.

The `DISPLAY` environment variable tells applications which X server to connect to:

```bash
export DISPLAY=:0  # Primary display
```

Without `DISPLAY` set (e.g., in a TTY without X), Rofi fails with "Cannot open display."

## Theory: The Keyboard-Driven Workflow

The i3 ecosystem is built around a **keyboard-driven workflow** philosophy:

1. **Minimize mouse usage**: The mouse is slow and imprecise compared to keyboard shortcuts.
2. **Modal interfaces**: Different modes (normal, insert, visual) for different tasks.
3. **Composability**: Small tools that work well together (Rofi + dmenu protocol + i3-msg).
4. **Status bar as dashboard**: The bar provides at-a-glance information and quick actions.

Clicktodo fits this philosophy by:

- Displaying the current task in the status bar (always visible).
- Supporting mouse clicks for quick actions (mark done, open VSCode, cycle).
- Providing a full Rofi UI for detailed management.
- Using keyboard-friendly dmenu-style menus.

## Theory: Unix Philosophy

Clicktodo follows several **Unix Philosophy** principles:

1. **Do one thing well**: Clicktodo manages todos. It doesn't try to be a project management tool, calendar, or note-taking app.
2. **Plain text configuration**: `i3status.conf` is a plain text file. `todos.json` is plain JSON.
3. **Composability**: Clicktodo integrates with other tools (i3, py3status, Rofi, VSCode) through well-defined interfaces.
4. **No dependencies**: The package has zero runtime dependencies beyond Python 3.10+.

The dmenu protocol is a perfect example of Unix composability: any tool that outputs newline-separated text can be used as a menu, and any tool that reads from stdin can be integrated into the workflow.
