# Python Concepts Used

## Overview

This document explains the Python language features and programming concepts used throughout the clicktodo codebase. Understanding these concepts is essential for reading, modifying, and extending the code.

## Python 3.10+ Features

The package requires Python 3.10 as a minimum. Key features from 3.10+ used in the codebase:

### Union Type Operator (`|`)

```python
def get_display_item(store: TodoStore) -> dict[str, Any] | None:
    ...
```

`str | None` means "either `str` or `None`". This replaces the older `Optional[str]` syntax from `typing`. It was introduced in Python 3.10 (PEP 604).

### Structural Pattern Matching (match/case)

Not used in this codebase, but available in Python 3.10+.

## Dataclasses

```python
from dataclasses import dataclass, field

@dataclass
class TodoItem:
    id: int
    text: str
    done: bool = False
    date: str | None = None
    environment: Environment | None = None
```

### How @dataclass Works

The `@dataclass` decorator automatically generates:

- `__init__(self, id, text, done=False, ...)` -- Constructor with keyword arguments.
- `__repr__(self)` -- Human-readable string representation.
- `__eq__(self, other)` -- Equality comparison (field-by-field).

Without `@dataclass`, you'd write 30+ lines of boilerplate.

### default_factory

```python
@dataclass
class Environment:
    opens: list[OpenItem] = field(default_factory=list)
```

For mutable default values (lists, dicts, sets), you must use `field(default_factory=...)`. This is because Python evaluates default values **once** at class definition time, not per instance. Without `default_factory`:

```python
# BAD - all instances share the SAME list:
opens: list = []
```

```python
# GOOD - each instance gets a NEW list:
opens: list = field(default_factory=list)
```

## Enumerations

```python
class AppLauncher(Enum):
    FIREFOX = "firefox"
    CODE = "code"
    CURSOR = "cursor"
    OKULAR = "okular"
    REMNOTE = "RemNote.AppImage"
```

An `Enum` defines a fixed set of named constants. Each member has a `name` and a `value`:

```python
AppLauncher.FIREFOX.name   # "FIREFOX"
AppLauncher.FIREFOX.value  # "firefox"
```

### Class Methods on Enums

The enum defines helper methods:

```python
@classmethod
def from_string(cls, value: str) -> "AppLauncher":
    try:
        return cls(value=value)
    except ValueError:
        return cls.CODE  # Default fallback
```

`@classmethod` means the method receives the class (`cls`) as its first argument, not an instance. This allows calling `AppLauncher.from_string("firefox")` without creating an instance first.

## Protocols (Structural Typing)

```python
from typing import Protocol

class UIBackend(Protocol):
    def show_menu(self, prompt: str, options: list[str]) -> str | None:
        ...
    def ask_text(self, prompt: str, initial: str = "") -> str | None:
        ...
```

A `Protocol` defines a structural interface. Any class that implements the required methods is considered compatible, even without explicit inheritance.

### Why Not Use ABCs?

Python has two ways to define interfaces:

| Approach | Type | Declaration | Use Case |
|---|---|---|---|
| `Protocol` | Structural | Implicit (duck typing) | When you don't control the implementing classes |
| `ABC` (Abstract Base Class) | Nominal | Explicit (`class X(Base):`) | When you control the class hierarchy |

`Protocol` is preferred here because:
- `RofiUI` doesn't need to declare `class RofiUI(UIBackend)`.
- Third-party implementations (wofi, fuzzel) don't need to import from clicktodo.
- The type checker verifies conformance automatically.

## Type Hints and Static Analysis

```python
def todo_counts(data: dict[str, Any]) -> tuple[int, int]:
    todos = data.get("todos", [])
    done = sum(1 for t in todos if t.get("done"))
    return done, len(todos)
```

Type hints serve three purposes:

1. **Documentation**: `dict[str, Any]` tells you the function accepts a dict with string keys.
2. **Static checking**: mypy verifies types at development time.
3. **IDE support**: Autocompletion, go-to-definition, and inline errors.

The codebase uses **gradual typing** -- type hints are present on most public APIs but not enforced on all internal code. This balances rigor with pragmatism.

### Common Type Annotations Used

| Annotation | Meaning |
|---|---|
| `str | None` | Optional string |
| `list[str]` | List of strings |
| `dict[str, Any]` | Dict with string keys, any value type |
| `Callable[[], None]` | Function that takes no args, returns None |
| `tuple[int, int]` | Two-element tuple of ints |
| `Path` | `pathlib.Path` object |
| `Protocol` | Structural interface |
| `TypeVar` | Generic type variable (not used here) |

## Decorators

### Function Decorators

```python
def register_migration(fn):
    _MIGRATIONS.append(fn)
    return fn

@register_migration
def _migration_v1_to_v2(data):
    pass
```

A decorator is a function that wraps another function. The `@decorator_name` syntax is syntactic sugar for `fn = decorator_name(fn)`.

### @classmethod and @staticmethod

```python
@classmethod
def from_dict(cls, data: dict) -> "TodoItem":
    ...

@staticmethod
def _get_extension(path: str) -> str:
    ...
```

- `@classmethod`: Receives the class as first argument (`cls`). Used for alternative constructors.
- `@staticmethod`: Receives no implicit first argument. Used for utility functions that logically belong to the class.

## pathlib -- Modern File System API

```python
from pathlib import Path

path = Path("/home/user/project")
path.parent           # /home/user
path.suffix           # ""
path.with_suffix(".json.tmp")  # /home/user/project.json.tmp
path.exists()         # True/False
path.read_text()      # File contents
path.mkdir(parents=True, exist_ok=True)  # Create directories
path.rename(new_path) # Atomic rename
```

`pathlib.Path` replaces the old `os.path` module. Benefits:

- **Object-oriented**: Method chaining instead of nested function calls.
- **Operator overloading**: `/` for path joining.
- **Cross-platform**: `Path` handles OS-specific path separators automatically.

## subprocess -- Process Management

Two patterns are used:

### subprocess.run() -- Blocking

```python
result = subprocess.run(
    ["rofi", "-dmenu", "-p", "Todos", "-i"],
    input=text,
    text=True,
    capture_output=True,
)
return result.stdout.strip() or None
```

Blocks until the process completes. Captures stdout/stderr. Used when you need the process output.

### subprocess.Popen() -- Non-blocking

```python
subprocess.Popen(
    argv,
    env=os.environ.copy(),
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    start_new_session=True,
)
```

Returns immediately. Used for fire-and-forget process spawning.

## shutil.which() -- Binary Detection

```python
ui_bin = shutil.which("clicktodo-ui")
if ui_bin:
    return [ui_bin, path]
```

`shutil.which(name)` searches `$PATH` for an executable. Returns the full path if found, `None` otherwise. Used to detect optional dependencies (rofi, i3-msg, code, py3-cmd) at runtime.

## shlex.split() -- Shell-Safe Tokenization

```python
import shlex
parts = shlex.split("my-ui --foo 'bar baz'")
# ['my-ui', '--foo', 'bar baz']
```

Splits a command string into tokens, respecting shell quoting rules. Prevents shell injection when executing user-provided commands.

## Theory: Why Python for This Project?

Clicktodo is written in Python because:

1. **Integration with py3status**: py3status modules must be Python.
2. **Rofi/dmenu communication**: Simple subprocess I/O, well-suited to Python.
3. **JSON handling**: Built-in `json` module is excellent for data serialization.
4. **Development speed**: Rapid prototyping and iteration.
5. **Zero dependencies**: The standard library provides everything needed (json, pathlib, subprocess, dataclasses, enum, typing).
6. **Cross-platform**: Runs on any platform with Python 3.10+ and X11 (for Rofi).
