"""Spawn the Rofi UI from the status bar or other callers."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from clicktodo.models import AppLauncher, Environment, OpenItem
from clicktodo.paths import default_data_path


def _debug_enabled() -> bool:
    return bool(os.environ.get("CLICKTODO_DEBUG"))


def _launch_log_path() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        base = Path(xdg).expanduser()
    else:
        base = Path.home() / ".local" / "share"
    return base / "clicktodo" / "launch.log"


# ---------------------------------------------------------------------------
# App launcher dispatch
# ---------------------------------------------------------------------------


def _launch_command(app: AppLauncher, target: str | None) -> list[str] | None:
    """Return the command argv for opening *target* with *app*, or None.

    When *target* is None, only apps that support a "launch-only" mode
    (firefox, RemNote) return a valid command.
    """

    if app == AppLauncher.FIREFOX:
        if shutil.which("firefox"):
            if target:
                return ["firefox", "--new-tab", target]
            return ["firefox"]
    elif app == AppLauncher.REMNOTE:
        if shutil.which("RemNote.AppImage"):
            if target:
                return ["RemNote.AppImage", target]
            return ["RemNote.AppImage"]
    elif app == AppLauncher.CODE:
        if not target:
            return None
        if shutil.which("code"):
            return ["code", "--reuse-window", target]
    elif app == AppLauncher.CURSOR:
        if not target:
            return None
        if shutil.which("cursor"):
            return ["cursor", target]
    elif app == AppLauncher.OKULAR:
        if not target:
            return None
        if shutil.which("okular"):
            return ["okular", target]

    return None


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


def launch_environment(env: Environment) -> None:
    """Open every item in *env.opens*."""
    for item in env.opens:
        launch_open_item(item)


# ---------------------------------------------------------------------------
# UI launcher (spawn the rofi/dmenu UI)
# ---------------------------------------------------------------------------


def ui_command(
    data_path: Path,
    *,
    custom_command: str = "",
) -> list[str]:
    """Argv for the UI process (no i3-msg wrapper)."""
    path = str(data_path.resolve())
    if custom_command.strip():
        parts = shlex.split(custom_command)
        return [*parts, path]

    ui_bin = shutil.which("clicktodo-ui")
    if ui_bin:
        return [ui_bin, path]
    return [sys.executable, "-m", "clicktodo.adapters.rofi.app", path]


def spawn_ui(
    data_path: Path | None = None,
    *,
    via_i3: bool = True,
    custom_command: str = "",
) -> None:
    """Start the Rofi UI, optionally wrapped with i3-msg exec."""
    path = data_path if data_path is not None else default_data_path()
    cmd = ui_command(path, custom_command=custom_command)

    if via_i3 and shutil.which("i3-msg"):
        argv = ["i3-msg", "-q", "exec", "--", *cmd]
        popen_kw: dict = {}
    else:
        argv = cmd
        popen_kw = {"start_new_session": True}

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

    subprocess.Popen(
        argv,
        env=os.environ.copy(),
        stdout=stdout_dest,
        stderr=stderr_dest,
        **popen_kw,
    )


# ---------------------------------------------------------------------------
# Auto-open displayed todo (for i3 autostart)
# ---------------------------------------------------------------------------


def open_displayed_environment(data_path: Path | None = None) -> None:
    """Open the environment items of the currently displayed todo.

    Loads the data file, resolves the displayed item (self-healing
    stale display_id), and opens all its environment open-items.
    Does nothing if there is no displayed todo or no environment.
    """
    from clicktodo.display import get_display_item
    from clicktodo.models import TodoItem
    from clicktodo.store import TodoStore

    path = data_path if data_path is not None else default_data_path()
    store = TodoStore(path)
    raw_item = get_display_item(store)
    if raw_item is None:
        return
    todo = TodoItem.from_dict(raw_item)
    if todo.environment is not None:
        launch_environment(todo.environment)


def main():
    """Console script entry point for clicktodo-open-environment."""
    open_displayed_environment()
