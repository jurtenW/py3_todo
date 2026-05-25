"""Notify py3status to refresh the bar module."""

from __future__ import annotations

import shutil
import subprocess


def refresh_status_bar(module: str = "clicktodo") -> None:
    if not shutil.which("py3-cmd"):
        return
    subprocess.run(
        ["py3-cmd", "refresh", module],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
