"""Rofi/dmenu interaction."""

from __future__ import annotations

import shutil
import subprocess
from typing import List, Optional


class RofiUI:
    def __init__(self):
        self.rofi_bin = shutil.which("rofi") or "dmenu"

    def show_menu(self, prompt: str, options: List[str]) -> Optional[str]:
        text = "\n".join(options)
        cmd = [self.rofi_bin, "-dmenu", "-p", prompt, "-i"]
        result = subprocess.run(cmd, input=text, text=True, capture_output=True)
        return result.stdout.strip() or None

    def ask_text(self, prompt: str, initial: str = "") -> Optional[str]:
        cmd = [self.rofi_bin, "-dmenu", "-p", prompt, "-lines", "0"]
        result = subprocess.run(cmd, input=initial, text=True, capture_output=True)
        return result.stdout.strip() or None
