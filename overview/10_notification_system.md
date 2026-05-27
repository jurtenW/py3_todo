# Notification System

## Overview

The `notify.py` module provides a single function: `refresh_status_bar()`. Its purpose is to tell py3status to re-render the clicktodo module after the data has been modified by another process (typically the Rofi UI).

## Implementation

```python
def refresh_status_bar(module: str = "clicktodo") -> None:
    if not shutil.which("py3-cmd"):
        return
    subprocess.run(
        ["py3-cmd", "refresh", module],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
```

### How It Works

1. **Check for py3-cmd**: `shutil.which("py3-cmd")` returns `None` if `py3-cmd` isn't installed. If so, the function returns silently -- no error.
2. **Run refresh command**: `py3-cmd refresh clicktodo` tells py3status to invalidate its cache for the `clicktodo` module and call its display method immediately.

### Why Notification Is Needed

The status bar uses a **caching model**: it only refreshes every `refresh_seconds` (default 5 seconds). Without notification, there would be a delay of up to 5 seconds between making a change in the Rofi UI and seeing it reflected in the status bar.

With notification, the update is **immediate**:

```
Rofi UI: add_todo()
    │
    ▼
TodoStore.save(refresh_bar=True)
    │
    ▼
refresh_status_bar()
    │
    ▼
py3-cmd refresh clicktodo
    │
    ▼
py3status calls clicktodo() immediately
    │
    ▼
Bar updates within ~100ms
```

### Defensive Design

The notification is **best-effort** and never fails loudly:

- If `py3-cmd` isn't installed: silent return.
- If `py3-cmd` fails (py3status isn't running): `check=False` ignores the non-zero exit code.
- Stdout/stderr are suppressed: no noise in the terminal.

This means the app works even without py3status (e.g., when used standalone or on a different window manager).

## Theory: Inter-Process Communication

The notification system is a form of **inter-process communication (IPC)**. The Rofi UI and py3status run as separate processes, and they need to coordinate when data changes.

### IPC Methods Compared

| Method | Latency | Complexity | Used By |
|---|---|---|---|
| `py3-cmd` (CLI) | ~100ms | Low | This project |
| Unix socket | ~1ms | Medium | Databases, web servers |
| Shared memory | ~0.1ms | High | High-performance systems |
| File polling | ~1s+ | Low | Simple file watchers |
| D-Bus | ~10ms | Medium | Desktop Linux apps |

`py3-cmd` is a CLI tool that communicates with the py3status process over a Unix domain socket. From the application's perspective, it's just a subprocess call -- simple and reliable.

### Why Not Use File Watching?

An alternative would be to have py3status watch the JSON file for changes (using `inotify` on Linux). This has trade-offs:

**File watching pros:**
- No coordination needed between processes.
- Works with any writer (not just the Rofi UI).

**File watching cons:**
- More complex to implement (need inotify bindings or polling loop).
- Potential for race conditions.
- Extra file descriptor overhead.
- py3status doesn't support file watching natively.

The `py3-cmd refresh` approach is simpler and fits the py3status architecture naturally.

## Theory: Best-Effort vs Failure-Fast

The notification system follows the **best-effort** pattern:

- **Best-effort**: Try to do something; if it fails, continue silently.
- **Failure-fast**: Raise an error immediately on failure.

Best-effort is appropriate for non-critical operations. If the notification fails:
- The data is still saved correctly (that's the critical part).
- The bar will eventually refresh on its own (after `refresh_seconds`).

Failure-fast is appropriate for critical operations. If `save()` fails, the error propagates because data loss is unacceptable.

Choosing the right pattern depends on the **blast radius** of failure. For notifications, the blast radius is small (delayed UI update). For persistence, the blast radius is large (data loss).
