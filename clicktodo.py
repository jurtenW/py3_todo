# -*- coding: utf-8 -*-
import json
import shlex
import subprocess
from pathlib import Path

_MODULE_DIR = Path(__file__).resolve().parent


def _resolve_module_path(configured: str) -> Path:
    path = Path(configured).expanduser()
    return path if path.is_absolute() else _MODULE_DIR / path


class Py3status:
    # --- Configuration (paths relative to this module unless absolute) ---
    data_path = "data/todos.json"
    ui_script = "scripts/clicktodo/clicktodo_ui_r.py"
    format = "✅ {done}/{total} • {next}"
    max_width = 40
    refresh_seconds = 5
    
    # --- State ---
    _path = None
    _ui_path = None

    def post_config_hook(self):
        """Initialize paths and ensure the file exists."""
        self._path = _resolve_module_path(self.data_path)
        self._ui_path = _resolve_module_path(self.ui_script)
        
        # Ensure data directory exists
        self._path.parent.mkdir(parents=True, exist_ok=True)
        
        # Ensure data file exists with default schema
        if not self._path.exists():
            default_state = {"todos": [], "archived": [], "display_id": 0, "seq": 0}
            self._write_json(default_state)

    # --- Helpers (The "Model") ---

    def _read_json(self):
        """Reads the state safely."""
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except (FileNotFoundError, json.JSONDecodeError):
            return {"todos": [], "archived": [], "display_id": 0, "seq": 0}

    def _write_json(self, data):
        """Writes the state atomically."""
        try:
            # Write to temp file first to avoid corruption on crash
            tmp_path = self._path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            tmp_path.rename(self._path)
        except Exception as e:
            self.py3.log(f"ClickTodo Save Error: {e}")

    def _get_display_item(self, data):
        """
        Determines which text to show based on display_id.
        Logic: 
        1. Try to find the task with ID == display_id.
        2. If not found or done, default to the first open task.
        3. If no open tasks, return None.
        """
        todos = data.get("todos", [])
        display_id = data.get("display_id", 0)
        
        open_todos = [t for t in todos if not t.get("done")]
        if not open_todos:
            return None

        # Try to find specific requested item
        for t in open_todos:
            if t.get("idx") == display_id:
                return t

        # Fallback: Default to first open item
        # We also update the state so the 'pointer' is valid again
        data["display_id"] = open_todos[0].get("idx")
        self._write_json(data)
        return open_todos[0]

    # --- The View ---

    def clicktodo(self):
        data = self._read_json()
        todos = data.get("todos", [])
        
        # Calculate stats
        done_count = sum(1 for t in todos if t.get("done"))
        total_count = len(todos)
        
        # Get current text
        item = self._get_display_item(data)
        if item:
            text = item.get("text", "")
            if len(text) > self.max_width:
                text = text[:self.max_width] + "…"
        else:
            text = "No Tasks"

        return {
            "full_text": self.py3.safe_format(self.format, {
                "done": done_count,
                "total": total_count,
                "next": text
            }),
            "cached_until": self.py3.time_in(self.refresh_seconds)
        }

    # --- The Controller (Input Handling) ---

    def on_click(self, event):
        button = event["button"]
        data = self._read_json()
        todos = data.get("todos", [])
        
        if button == 1: # Left Click: Launch UI
            # We pass the data path to the UI script
            cmd = f"i3-msg -q exec -- python3 {shlex.quote(str(self._ui_path))} {shlex.quote(str(self._path))}"
            subprocess.Popen(cmd, shell=True)
            return

        elif button == 2: # Middle Click: Mark current displayed task as done
            item = self._get_display_item(data)
            if item:
                # Find the actual reference in the list and update it
                for t in todos:
                    if t["idx"] == item["idx"]:
                        t["done"] = True
                        break
                self._write_json(data)

        elif button == 3: # Right Click: Toggle/Un-do (Simple logic: undo last done?)
            # For simplicity, let's make Right Click 'Add New' or 'Launch UI' 
            # OR logic: Un-mark the most recently done task? 
            # Let's stick to your original: Reopen first done task
            for t in reversed(todos): # Reverse to find most recent?
                if t.get("done"):
                    t["done"] = False
                    break
            self._write_json(data)

        elif button == 4: # Scroll Up (Previous Task)
            self._cycle_display(data, -1)

        elif button == 5: # Scroll Down (Next Task)
            self._cycle_display(data, 1)
            
    def _cycle_display(self, data, direction):
        """Rotates the display_id through the list of OPEN tasks."""
        todos = data.get("todos", [])
        open_todos = [t for t in todos if not t.get("done")]
        
        if not open_todos:
            return

        current_id = data.get("display_id")
        
        # Find current index in the OPEN list
        current_idx = 0
        for i, t in enumerate(open_todos):
            if t["idx"] == current_id:
                current_idx = i
                break
        
        # Calculate new index with wrap-around
        new_idx = (current_idx + direction) % len(open_todos)
        
        # Save new ID
        data["display_id"] = open_todos[new_idx]["idx"]
        self._write_json(data)