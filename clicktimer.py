# ~/.config/py3status/modules/clicktimer.py
# A minimal click-to-run timer for py3status.

from pathlib import Path
import json
import time


def translate_json_idx_all(idx, todos) -> int:
    for i,t in enumerate(todos):
        if t["idx"] == idx:
            return i
    return 0


class Py3status:
    # --- user options (override in config) ---
    format_running = "⏱ {duration}"
    format_stopped = "⏸ {duration}|(stopped)"
    color = None  # e.g. "#bfbaac"

    data_path = "~/.local/share/clicktodo/todos.json"
    max_next_len = 40
    refresh_seconds = 1

    _path = None
    _init_error = None

    def post_config_hook(self):
        try:
            p = Path(self.data_path).expanduser()
            p.parent.mkdir(parents=True, exist_ok=True)
            if p.exists() and p.is_dir():
                backup = p.with_name(p.name + ".dir.bak")
                p.rename(backup)
                self.py3.log(f"clicktodo: '{p}' was a directory. Moved to '{backup}'.")
            if not p.exists():
                p.write_text(json.dumps({"todos": [], "archived": [], "display_id": 0, "counter": 0}, ensure_ascii=False),
                             encoding="utf-8")
            self._path = p
        except Exception as e:
            self._init_error = f"init: {e.__class__.__name__}"
            self.py3.log(f"clicktodo init error: {e}")

    def _load(self):
        """Load state safely. On JSON/IO error, back up and reset."""
        try:
            txt = self._path.read_text(encoding="utf-8")
            data = json.loads(txt)
            if not isinstance(data, dict):
                raise ValueError("state is not a dict")
            data.setdefault("todos", [])
            data.setdefault("archived", [])
            return data
        except Exception as e:
            try:
                bad = self._path.with_suffix(self._path.suffix + ".bad")
                self._path.rename(bad)
                self.py3.log(f"clicktodo: corrupt state moved to '{bad}': {e}")
            except Exception as e2:
                self.py3.log(f"clicktodo: failed to backup corrupt state: {e2}")

    def _save(self, st):
        try:
            self._path.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            self.py3.log(f"clicktodo save error: {e}")
     
    def _format_secs(self, secs: int) -> str:
        if secs < 0:
            secs = 0
        d, r = divmod(secs, 86400)
        h, r = divmod(r, 3600)
        m, s = divmod(r, 60)
        if d:
            return f"{d}d {h:02d}:{m:02d}:{s:02d}"
        if h:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def _current_elapsed(self) -> int:
        st = self._load()["clock"]
        if st["running"]:
            return int(st["elapsed"] + (time.time() - st["start"]))
        return int(st["elapsed"])

    def clicktimer(self):
        st_all = self._load()
        open = [t for t in st_all["todos"] if not t.get("done")]
        st = st_all["clock"]

        elapsed = self._current_elapsed()
        timer_id = st["timer_id"]
        display_id = st_all["display_id"]
        display_id_idx = open[display_id]["idx"]
        idx = translate_json_idx_all(display_id_idx, st_all["todos"]) # Ist nicht mehr valide wenn man einen Task direkt beendet

        if timer_id != display_id:
            st["start"] = time.time()
            st["elapsed"] = 0.0
            st["timer_id"] = display_id
            self._save(st_all)
            elapsed = 0.0

        display = int(elapsed + open[display_id]["time"])
        if st["running"]:
            text = self.py3.safe_format(self.format_running, {"duration": self._format_secs(display)})
            resp = {"full_text": text, "cached_until": self.py3.time_in(1)}
        else:
            text = self.py3.safe_format(self.format_stopped, {"duration": self._format_secs(display)})
            resp = {"full_text": text, "cached_until": self.py3.CACHE_FOREVER}
        if self.color:
            resp["color"] = self.color
        return resp

    def on_click(self, event):
        btn = event.get("button")
        st_all = self._load()
        st = st_all["clock"]

        # Left click: start/stop toggle
        if btn == 1:
            now = time.time()
            if not st["running"]:
                st["running"] = True
                st["start"] = now
            else:
                # stop and accumulate
                st["elapsed"] += now - st["start"]
                st["running"] = False
                st["start"] = 0.0
            self._save(st_all)
            self.py3.update()

        # Right click: reset
        elif btn == 3:
            st.update({"running": False, "start": 0.0, "elapsed": 0.0})
            self._save(st_all)
            self.py3.update()

