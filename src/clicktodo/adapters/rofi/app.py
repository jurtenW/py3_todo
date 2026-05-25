#!/usr/bin/env python3
"""Rofi todo manager."""

from __future__ import annotations

import datetime
import sys
from pathlib import Path
from typing import Callable, Dict, List

from clicktodo.models import TodoItem
from clicktodo.paths import default_data_path, module_root, resolve_path
from clicktodo.store import TodoStore

from clicktodo.adapters.rofi.ui import RofiUI


class TodoApp:
    def __init__(self, store: TodoStore, ui: RofiUI):
        self.store = store
        self.ui = ui

    def run(self) -> None:
        while True:
            menu_map = self._build_main_menu_map()
            selection = self.ui.show_menu("Todos", list(menu_map.keys()))
            if not selection:
                break
            action = menu_map.get(selection)
            if action:
                action()

    def _build_main_menu_map(self) -> Dict[str, Callable[[], None]]:
        mapping: Dict[str, Callable[[], None]] = {}
        mapping["+ Add new…"] = self.prompt_add_new
        todos = self.store.get_todos()

        def date_sort_key(t: TodoItem):
            if not t.date:
                return datetime.datetime.max
            try:
                return datetime.datetime.strptime(t.date, "%d.%m.%Y")
            except ValueError:
                return datetime.datetime.max

        open_todos = sorted([t for t in todos if not t.done], key=date_sort_key)
        done_todos = [t for t in todos if t.done]

        for t in open_todos:
            label = f"[#{t.id}] [{t.date or 'DO IT'}] {t.text}"
            mapping[label] = lambda item=t: self.handle_item_actions(item)

        for t in done_todos:
            label = f"[DONE] {t.text}"
            mapping[label] = lambda item=t: self.handle_item_actions(item)

        long_term = self.store.get_long_term()
        mapping[f"⋯ Long-term ({len(long_term)})"] = self.show_long_term_menu
        mapping[f"⋯ Archived ({len(self.store.data.get('archived', []))})"] = (
            self.show_archive_menu
        )
        mapping["Archive finished tasks"] = self.archive_finished_tasks
        return mapping

    def archive_finished_tasks(self) -> None:
        self.store.archive_finished_todos()

    def prompt_add_new(self) -> None:
        text = self.ui.ask_text("New Task")
        if text:
            date = self.ui.ask_text(
                "Deadline (DD.MM.YYYY)",
                datetime.datetime.now().strftime("%d.%m.%Y"),
            )
            self.store.add_todo(text, date)

    def handle_item_actions(self, item: TodoItem) -> None:
        options = [
            "Toggle Done",
            "Display",
            "Edit Text",
            "Edit Date",
            "Delete",
            "Archive",
            "Back",
        ]
        choice = self.ui.show_menu(f"Action: {item.text}", options)

        if choice == "Toggle Done":
            item.done = not item.done
            self.store.update_todo(item)
        elif choice == "Display":
            self.store.set_display_id(item.id)
        elif choice == "Edit Text":
            new_text = self.ui.ask_text("Edit", item.text)
            if new_text:
                item.text = new_text
                self.store.update_todo(item)
        elif choice == "Delete":
            self.store.delete_todo(item.id)
        elif choice == "Archive":
            self.store.archive_todo(item)

    def show_archive_menu(self) -> None:
        while True:
            archived = self.store.get_archived_items()
            if not archived:
                self.ui.show_menu("Archived", ["(empty)", "Back"])
                return

            mapping: Dict[str, Callable[[], None]] = {"Back": lambda: None}
            for item in archived:
                label = f"[#{item.id}] {item.text}"
                mapping[label] = lambda i=item: self._archive_item_actions(i)

            selection = self.ui.show_menu("Archived", list(mapping.keys()))
            if not selection or selection == "Back":
                return
            action = mapping.get(selection)
            if action:
                action()
                if selection == "Back":
                    return

    def _archive_item_actions(self, item: TodoItem) -> None:
        choice = self.ui.show_menu(
            f"Archived: {item.text}",
            ["Restore to todos", "Delete permanently", "Back"],
        )
        if choice == "Restore to todos":
            self.store.restore_archived(item.id)
        elif choice == "Delete permanently":
            self.store.delete_archived(item.id)

    def show_long_term_menu(self) -> None:
        while True:
            items = self.store.get_long_term()
            mapping: Dict[str, Callable[[], None]] = {
                "+ Add long-term…": self._prompt_add_long_term,
                "Back": lambda: None,
            }
            for i, entry in enumerate(items):
                text = entry.get("text", "(untitled)")
                mapping[f"{i + 1}. {text}"] = lambda idx=i: self._long_term_actions(idx)

            selection = self.ui.show_menu("Long-term", list(mapping.keys()))
            if not selection or selection == "Back":
                return
            action = mapping.get(selection)
            if action:
                action()

    def _prompt_add_long_term(self) -> None:
        text = self.ui.ask_text("Long-term idea")
        if text:
            self.store.add_long_term(text)

    def _long_term_actions(self, index: int) -> None:
        items = self.store.get_long_term()
        if index >= len(items):
            return
        text = items[index].get("text", "")
        choice = self.ui.show_menu(
            text,
            ["Promote to active todo", "Remove", "Back"],
        )
        if choice == "Promote to active todo":
            self.store.promote_long_term(index)
        elif choice == "Remove":
            self.store.remove_long_term(index)


def main() -> None:
    path_arg = sys.argv[1] if len(sys.argv) > 1 else str(default_data_path())
    db_path = Path(path_arg).expanduser()
    if not db_path.is_absolute():
        db_path = resolve_path(str(db_path), module_root())

    store = TodoStore(db_path)
    store.ensure_file()
    TodoApp(store, RofiUI()).run()


if __name__ == "__main__":
    main()
