# Clicktodo

Todo list for the i3/sway status bar via [py3status](https://github.com/ultrabug/py3status), with a Rofi UI for full editing.

## Install

```bash
cd /path/to/py3_todo
pip install -e .
```

Symlink the py3status module (module name must match the filename `clicktodo`):

```bash
mkdir -p ~/.config/py3status/modules
ln -sf "$(pwd)/modules/clicktodo.py" ~/.config/py3status/modules/clicktodo.py
```

Alternatively, point py3status at this repo:

```text
status_command py3status -c ~/.config/i3/i3status.conf -i /path/to/py3_todo
```

Add to `i3status.conf`:

```text
order += "clicktodo"
clicktodo {
    data_path = "/home/USER/.local/share/clicktodo/todos.json"
    format = "✅ {done}/{total} • {next}"
    max_width = 40
    refresh_seconds = 5
}
```

If `data_path` is omitted, the default is `~/.local/share/clicktodo/todos.json`.

After UI changes, the bar is refreshed with `py3-cmd refresh clicktodo` (handled automatically).

## Status bar controls

| Input | Action |
|-------|--------|
| Left click (btn 1) | Open Rofi UI (`clicktodo-ui`) |
| Middle click (btn 2) | Mark the displayed open task as done |
| Right click (btn 3) | Undo the most recently completed task |
| Scroll up (btn 4) | Previous open task (`display_id`) |
| Scroll down (btn 5) | Next open task |

## CLI

```bash
clicktodo-ui                          # uses default data path
clicktodo-ui ~/.local/share/clicktodo/todos.json
```

## Data file

Live data lives at `~/.local/share/clicktodo/todos.json` by default. See [`data/todos.json.example`](data/todos.json.example) for the schema.

Migrate from the repo copy once:

```bash
mkdir -p ~/.local/share/clicktodo
cp data/todos.json ~/.local/share/clicktodo/todos.json   # if you used repo data before
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Project layout

- `modules/clicktodo.py` — thin py3status shim (symlink target; not at repo root to avoid import shadowing)
- `src/clicktodo/` — shared models, store, display logic
- `src/clicktodo/adapters/py3status_bar.py` — bar module implementation
- `src/clicktodo/adapters/rofi/` — Rofi UI

## Roadmap

- **clock** — JSON field preserved for a future timer feature; not shown in the bar or Rofi yet.
- **long-term** — backlog list in Rofi (view/add/promote to active todos).
