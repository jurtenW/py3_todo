# Path Resolution

## Overview

The `paths.py` module provides helpers for resolving file paths. It handles three concerns:

1. Finding the **module root** (repository/package root directory).
2. Finding the **XDG-compliant data directory** for user data.
3. Resolving **relative vs absolute paths** from configuration.

## Functions

### module_root()

```python
_MODULE_DIR = Path(__file__).resolve().parents[2]

def module_root() -> Path:
    return _MODULE_DIR
```

Returns the package root directory (parent of `src/clicktodo/`). Uses `__file__` (the path of this file) to navigate up the directory tree:

```
__file__ = /home/user/.../src/clicktodo/paths.py
.parents[0] = /home/user/.../src/clicktodo/
.parents[1] = /home/user/.../src/
.parents[2] = /home/user/.../   <-- module_root
```

The `_MODULE_DIR` is computed at module import time and cached. This is more reliable than using `os.getcwd()` because the working directory can change between calls.

### default_data_path()

```python
def default_data_path() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        base = Path(xdg).expanduser()
    else:
        base = Path.home() / ".local" / "share"
    return base / "clicktodo" / "todos.json"
```

Returns the default data file path following the **XDG Base Directory Specification**:

| Environment | Default Path |
|---|---|
| `$XDG_DATA_HOME` set | `$XDG_DATA_HOME/clicktodo/todos.json` |
| `$XDG_DATA_HOME` not set | `~/.local/share/clicktodo/todos.json` |

The `expanduser()` call handles `~` in the environment variable (e.g., `$XDG_DATA_HOME=~/.data`).

### resolve_path()

```python
def resolve_path(configured: str, base: Path | None = None) -> Path:
    path = Path(configured).expanduser()
    if path.is_absolute():
        return path
    root = base if base is not None else module_root()
    return root / path
```

Resolves a configured path string to an absolute path:

| Input | Resolution |
|---|---|
| `/absolute/path.json` | Returned as-is |
| `~/home/path.json` | Expanded to `/home/user/path.json` |
| `data/todos.json` | Relative to `module_root()` → `/repo/root/data/todos.json` |
| `data/todos.json` (with `base=tmp_path`) | Relative to `base` → `/tmp/.../data/todos.json` |

## Theory: XDG Base Directory Specification

The **XDG Base Directory Specification** (freedesktop.org) standardizes where applications store data, configuration, and caches on Linux/Unix systems. This avoids cluttering the home directory with dotfiles.

| Variable | Purpose | Default |
|---|---|---|
| `XDG_DATA_HOME` | User data files | `~/.local/share` |
| `XDG_CONFIG_HOME` | User configuration files | `~/.config` |
| `XDG_CACHE_HOME` | Non-essential cached data | `~/.cache` |

Clicktodo stores its data (`todos.json`) in `XDG_DATA_HOME` because:
- It's user-generated data (not application configuration).
- It should persist across reinstalls.
- It's not cache data that can be regenerated.

### Why Not Use `~/.clicktodo/todos.json`?

The old convention of putting everything in the home directory as dotfiles (`~/.clicktodo/`) has been deprecated in favor of XDG. Benefits of XDG:

1. **Cleaner home directory**: No more `~/.config`, `~/.cache`, `~/.local` sprawl.
2. **Portable**: Users can set `XDG_DATA_HOME=/mnt/data` to store all app data on an external drive.
3. **Consistent**: Other apps follow the same convention, making it predictable.

## Theory: Path Resolution in Python

Python's `pathlib.Path` provides a modern, object-oriented API for file system paths:

| Operation | `os.path` (old) | `pathlib.Path` (new) |
|---|---|---|
| Join | `os.path.join(a, b)` | `a / b` |
| Parent | `os.path.dirname(p)` | `p.parent` |
| Exists | `os.path.exists(p)` | `p.exists()` |
| Read text | `open(p).read()` | `p.read_text()` |
| Expand `~` | `os.path.expanduser(p)` | `Path(p).expanduser()` |
| Resolve symlinks | `os.path.realpath(p)` | `p.resolve()` |

The `/` operator for path joining is the key feature. It's commutative with strings:

```python
Path("/home/user") / "project" / "src"  # /home/user/project/src
```

### resolve(strict=False)

The `resolve()` method resolves a path to its absolute, canonical form (resolving symlinks, `..`, and `.`). The `strict=False` parameter (Python 3.6+) means it doesn't raise an error if the path doesn't exist:

```python
Path("/nonexistent/dir").resolve(strict=False)  # Returns the path
Path("/nonexistent/dir").resolve(strict=True)   # Raises FileNotFoundError
```

This is used in the Rofi UI when resolving environment paths that may not exist yet (e.g., a future project directory).

## Theory: __file__ and Module Paths

The `__file__` attribute is automatically set by Python to the path of the module file. It's a reliable way to find files relative to the package:

```python
__file__ = "/home/user/venv/lib/python3.13/site-packages/clicktodo/paths.py"
```

Using `__file__` is better than `os.getcwd()` because:
- `getcwd()` depends on where the command was run from (unpredictable).
- `__file__` is always the path of the actual module file (deterministic).
- It works even when the package is installed in a virtual environment or system site-packages.

The `.resolve()` call converts the path to an absolute path and resolves any symlinks, so the result is canonical.
