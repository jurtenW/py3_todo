"""Spawn the Rofi UI from the status bar or other callers."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

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
