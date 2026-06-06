"""Rofi/dmenu interaction."""

from __future__ import annotations

import shutil
import subprocess
from typing import Protocol


class UIBackend(Protocol):
    """Minimal UI protocol supporting menu selection and text input.

    Implementations: RofiUI (production), MockUI (testing), wofi, fuzzel, etc.
    """

    def show_menu(self, prompt: str, options: list[str]) -> str | None:
        ...

    def ask_text(self, prompt: str, initial: str = "") -> str | None:
        ...


class RofiUI:
    """Production UI backed by ``rofi -dmenu`` (falls back to ``dmenu``)."""

    def __init__(self) -> None:
        self.rofi_bin = shutil.which("rofi") or "dmenu"

    def show_menu(self, prompt: str, options: list[str]) -> str | None:
        text = "\n".join(options)
        cmd = [self.rofi_bin, "-dmenu", "-p", prompt, "-i"]
        result = subprocess.run(cmd, input=text, text=True, capture_output=True)
        return result.stdout.strip() or None

    def ask_text(self, prompt: str, initial: str = "") -> str | None:
        cmd = [self.rofi_bin, "-dmenu", "-p", prompt, "-lines", "0"]
        result = subprocess.run(cmd, input=initial, text=True, capture_output=True)
        if result.returncode != 0:
            return None  # user cancelled (Escape, etc.)
        return result.stdout.strip()
