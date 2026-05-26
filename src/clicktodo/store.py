"""Persistent todo store with atomic writes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from clicktodo.models import TodoItem, default_state, normalize_state
from clicktodo.notify import refresh_status_bar


class TodoStore:
    def __init__(self, filepath: Path):
        self.filepath = Path(filepath)
        self.data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.filepath.exists():
            return default_state()
        try:
            raw = json.loads(self.filepath.read_text(encoding="utf-8"))
            return normalize_state(raw)
        except (json.JSONDecodeError, OSError):
            return default_state()

    def ensure_file(self) -> None:
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        if not self.filepath.exists():
            self.save()

    def save(self, *, refresh_bar: bool = False, indent: bool = True) -> None:
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.filepath.with_suffix(self.filepath.suffix + ".tmp")
        payload = json.dumps(
            self.data,
            ensure_ascii=False,
            indent=2 if indent else None,
        )
        tmp_path.write_text(payload, encoding="utf-8")
        tmp_path.rename(self.filepath)
        if refresh_bar:
            refresh_status_bar()

    def reload(self) -> None:
        self.data = self._load()

    def get_todos(self) -> list[TodoItem]:
        return [TodoItem.from_dict(x) for x in self.data.get("todos", [])]

    def add_todo(self, text: str, date: str | None = None) -> TodoItem:
        new_id = self.data.get("seq", 0) + 1
        self.data["seq"] = new_id
        item = TodoItem(id=new_id, text=text, date=date)
        self.data["todos"].append(item.to_dict())
        self.data["display_id"] = new_id
        self.save(refresh_bar=True)
        return item

    def update_todo(self, item: TodoItem) -> None:
        for i, raw in enumerate(self.data["todos"]):
            if raw.get("idx") == item.id:
                self.data["todos"][i] = item.to_dict()
                break
        self.save(refresh_bar=True)

    def delete_todo(self, item_id: int) -> None:
        self.data["todos"] = [
            t for t in self.data["todos"] if t.get("idx") != item_id
        ]
        self.save(refresh_bar=True)

    def archive_todo(self, item: TodoItem) -> None:
        self.data["archived"].append(item.to_dict())
        self.data["todos"] = [
            t for t in self.data["todos"] if t.get("idx") != item.id
        ]
        self.save(refresh_bar=True)

    def archive_finished_todos(self) -> None:
        for item in self.get_todos():
            if item.done:
                self.data["archived"].append(item.to_dict())
        self.data["todos"] = [t for t in self.data["todos"] if not t.get("done")]
        self.save(refresh_bar=True)

    def set_display_id(self, item_id: int) -> None:
        self.data["display_id"] = item_id
        self.save(refresh_bar=True)

    def mark_done_by_idx(self, idx: int) -> None:
        for t in self.data["todos"]:
            if t.get("idx") == idx:
                t["done"] = True
                break
        self.save()

    def undo_last_done(self) -> bool:
        for t in reversed(self.data["todos"]):
            if t.get("done"):
                t["done"] = False
                self.save()
                return True
        return False

    def get_long_term(self) -> list[dict[str, Any]]:
        return list(self.data.get("long-term") or [])

    def add_long_term(self, text: str) -> None:
        self.data.setdefault("long-term", []).append({"text": text})
        self.save(refresh_bar=True)

    def promote_long_term(self, index: int) -> None:
        lt = self.data.setdefault("long-term", [])
        if index < 0 or index >= len(lt):
            return
        entry = lt.pop(index)
        text = entry.get("text", "")
        if text:
            new_id = self.data.get("seq", 0) + 1
            self.data["seq"] = new_id
            item = TodoItem(id=new_id, text=text)
            self.data["todos"].append(item.to_dict())
            self.data["display_id"] = new_id
        self.save(refresh_bar=True)

    def remove_long_term(self, index: int) -> None:
        lt = self.data.setdefault("long-term", [])
        if 0 <= index < len(lt):
            lt.pop(index)
            self.save(refresh_bar=True)

    def get_archived_items(self) -> list[TodoItem]:
        return [TodoItem.from_dict(x) for x in self.data.get("archived", [])]

    def restore_archived(self, item_id: int) -> None:
        archived = self.data.get("archived", [])
        for i, raw in enumerate(archived):
            if raw.get("idx") == item_id:
                item = TodoItem.from_dict(raw)
                item.done = False
                self.data["todos"].append(item.to_dict())
                del archived[i]
                self.save(refresh_bar=True)
                return

    def delete_archived(self, item_id: int) -> None:
        self.data["archived"] = [
            t for t in self.data.get("archived", []) if t.get("idx") != item_id
        ]
        self.save(refresh_bar=True)
