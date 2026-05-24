#!/usr/bin/env python3
import json
import shutil
import subprocess
import sys
import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass

# ==========================================
# 1. THE MODEL (Data & State Management)
# ==========================================

@dataclass
class TodoItem:
    """Represents a single task to ensure consistent data structure."""
    id: int
    text: str
    done: bool = False
    date: Optional[str] = None
    created_at: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TodoItem':
        return cls(
            id=data.get("idx", 0),
            text=data.get("text", ""),
            done=data.get("done", False),
            date=data.get("date"),
            created_at=data.get("time", 0)
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "idx": self.id,
            "text": self.text,
            "done": self.done,
            "date": self.date,
            "time": self.created_at
        }

class TodoStore:
    """Handles all file operations and data manipulation."""
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if not self.filepath.exists():
            return {"todos": [], "archived": [], "long-term": [], "seq": 0, "display_id": 0}
        try:
            return json.loads(self.filepath.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"todos": [], "archived": [], "long-term": [], "seq": 0, "display_id": 0}

    def save(self):
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self.filepath.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        subprocess.run(["sh", "-lc", "py3-cmd refresh clicktodo >/dev/null 2>&1"])

    def add_todo(self, text: str, date: Optional[str] = None):
        new_id = self.data.get("seq", 0) + 1
        self.data["seq"] = new_id
        new_item = TodoItem(id=new_id, text=text, date=date)
        self.data["todos"].append(new_item.to_dict())
        self.data["display_id"] = new_id
        self.save()

    def get_todos(self) -> List[TodoItem]:
        return [TodoItem.from_dict(x) for x in self.data.get("todos", [])]

    def update_todo(self, item: TodoItem):
        for i, raw in enumerate(self.data["todos"]):
            if raw.get("idx") == item.id:
                self.data["todos"][i] = item.to_dict()
                break
        self.save()

    def delete_todo(self, item_id: int):
        self.data["todos"] = [t for t in self.data["todos"] if t.get("idx") != item_id]
        self.save()

    def archive_todo(self, item: TodoItem):
        self.data["archived"].append(item.to_dict())
        self.delete_todo(item.id)

    def archive_finished_todos(self):
        todos = self.get_todos()
        for todo in todos:
            if todo.done:
                self.archive_todo(todo)
        self.save()

# ==========================================
# 2. THE VIEW (Rofi Interface)
# ==========================================

class RofiUI:
    """Handles interaction with Rofi/Dmenu."""
    def __init__(self):
        self.rofi_bin = shutil.which("rofi") or "dmenu"

    def show_menu(self, prompt: str, options: List[str]) -> Optional[str]:
        """Displays a menu and returns the selected string."""
        text = "\n".join(options)
        cmd = [self.rofi_bin, "-dmenu", "-p", prompt, "-i"] # -i for case insensitive
        
        result = subprocess.run(cmd, input=text, text=True, capture_output=True)
        return result.stdout.strip() or None

    def ask_text(self, prompt: str, initial: str = "") -> Optional[str]:
        """Asks the user for text input."""
        cmd = [self.rofi_bin, "-dmenu", "-p", prompt, "-lines", "0"]
        result = subprocess.run(cmd, input=initial, text=True, capture_output=True)
        return result.stdout.strip() or None

# ==========================================
# 3. THE CONTROLLER (Application Logic)
# ==========================================

class TodoApp:
    def __init__(self, store: TodoStore, ui: RofiUI):
        self.store = store
        self.ui = ui

    def run(self):
        """Main Event Loop"""
        while True:
            menu_map = self._build_main_menu_map()
            
            choices = list(menu_map.keys())
            selection = self.ui.show_menu("Todos", choices)

            if not selection:
                break
            
            if selection in menu_map:
                action = menu_map[selection]
                action()

    def _build_main_menu_map(self) -> Dict[str, Callable]:
        """Constructs the main menu and maps choices to actions."""
        mapping = {}

        mapping["+ Add new…"] = self.prompt_add_new
        todos = self.store.get_todos()

        def date_sort_key(t: TodoItem):
            """Parses DD.MM.YYYY string to a datetime object for correct sorting."""
            if not t.date:
                # If no date, push to the very end (year 9999)
                return datetime.datetime.max
            try:
                # Convert "30.01.2025" -> datetime object
                return datetime.datetime.strptime(t.date, "%d.%m.%Y")
            except ValueError:
                # If the user typed a malformed date, push it to the end
                return datetime.datetime.max

        open_todos = sorted(
            [t for t in todos if not t.done], 
            key=date_sort_key
        )
        
        done_todos = [t for t in todos if t.done]

        for t in open_todos:
            label = f"[#{t.id}] [{t.date or 'DO IT'}] {t.text}"
            mapping[label] = lambda item=t: self.handle_item_actions(item)

        for t in done_todos:
            label = f"[DONE] {t.text}"
            mapping[label] = lambda item=t: self.handle_item_actions(item)

        mapping[f"⋯ Archived ({len(self.store.data.get('archived', []))})"] = self.show_archive_menu
        mapping[f"Archive Tasks"] = self.archive_finished_tasks 
        return mapping

    def archive_finished_tasks(self):
        self.store.archive_finished_todos()

    def prompt_add_new(self):
        text = self.ui.ask_text("New Task")
        if text:
            date = self.ui.ask_text("Deadline (DD.MM.YYYY)", datetime.datetime.now().strftime("%d.%m.%Y"))
            self.store.add_todo(text, date)

    def handle_item_actions(self, item: TodoItem):
        """Sub-menu for a specific item."""
        options = ["Toggle Done","Display", "Edit Text", "Edit Date", "Delete", "Archive", "Back"]
        choice = self.ui.show_menu(f"Action: {item.text}", options)

        if choice == "Toggle Done":
            item.done = not item.done
            self.store.update_todo(item)
        elif choice == "Display":
            self.store.data["display_id"] = item.id
            self.store.save()
        elif choice == "Edit Text":
            new_text = self.ui.ask_text("Edit", item.text)
            if new_text:
                item.text = new_text
                self.store.update_todo(item)
        elif choice == "Delete":
            self.store.delete_todo(item.id)
        elif choice == "Archive":
            self.store.archive_todo(item)

    def show_archive_menu(self):
        # Implementation similar to _build_main_menu_map but for archives
        pass

# ==========================================
# ENTRY POINT
# ==========================================

def main():
    path_arg = sys.argv[1] if len(sys.argv) > 1 else "~/Jurten/py3_todo/data/todos.json"
    db_path = Path(path_arg).expanduser()
    
    store = TodoStore(db_path)
    ui = RofiUI()
    app = TodoApp(store, ui)
    
    # Start
    app.run()

if __name__ == "__main__":
    main()
