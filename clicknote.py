# ~/.config/py3status/modules/clicknote.py
from pathlib import Path
import os
import shlex

class Py3status:
    note_path = "~/.config/py3status/note.txt"
    format = "📝 {text}|(empty)"
    max_len = 120
    ellipsis = "…"
    color = None

    def post_config_hook(self):
        self._path = Path(os.path.expanduser(self.note_path))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("", encoding="utf-8")

    def _read(self):
        try:
            t = self._path.read_text(encoding="utf-8").strip()
        except Exception:
            t = ""
        if self.max_len and len(t) > self.max_len:
            t = t[: self.max_len - 1] + self.ellipsis
        return t

    def clicknote(self):
        resp = {
            "full_text": self.py3.safe_format(self.format, {"text": self._read()}),
            "cached_until": self.py3.CACHE_FOREVER,
        }
        if self.color:
            resp["color"] = self.color
        return resp

    def on_click(self, event):
        btn = event.get("button")
        note_file = shlex.quote(str(self._path))
        if btn == 1:
            # Ask i3 to exec the helper script (i3 manages focus safely)
            cmd = f"i3-msg -q exec -- ~/.local/bin/clicknote_prompt.sh {note_file}"
            self.py3.command_run(cmd)
        elif btn == 2:
            self._path.write_text("", encoding="utf-8")
            self.py3.update()
        elif btn == 3:
            editor = os.environ.get("EDITOR", "nano")
            terminal = os.environ.get("TERMINAL", "")
            if terminal:
                self.py3.command_run(f"{terminal} -e {editor} {note_file}")
            else:
                self.py3.command_run(
                    f"alacritty -e {editor} {note_file} || "
                    f"kitty -e {editor} {note_file} || "
                    f"gnome-terminal -- {editor} {note_file} || "
                    f"xterm -e {editor} {note_file} || "
                    f"{editor} {note_file}"
                )

