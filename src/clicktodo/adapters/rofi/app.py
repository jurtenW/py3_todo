#!/usr/bin/env python3
"""Rofi todo manager."""

from __future__ import annotations

import datetime
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from clicktodo import display, launch
from clicktodo.adapters.rofi.ui import RofiUI
from clicktodo.models import AppLauncher, Environment, OpenItem, TodoItem
from clicktodo.paths import default_data_path, module_root, resolve_path
from clicktodo.store import TodoStore


class TodoApp:
    def __init__(self, store: TodoStore, ui: RofiUI):
        self.store = store
        self.ui = ui

    def _resolve_env_path(self, raw: str) -> str:
        """Resolve possibly-relative paths to an absolute path.

        URLs (``http://`` / ``https://``) are returned unchanged.
        """
        s = raw.strip()
        if not s:
            return ""

        # Pass URLs through without filesystem resolution.
        if s.startswith(("http://", "https://")):
            return s

        p = Path(s).expanduser()
        if not p.is_absolute():
            p = self.store.filepath.parent / p

        # strict=False avoids errors if the directory doesn't exist yet.
        return str(p.resolve(strict=False))

    def run(self) -> None:
        while True:
            menu_map = self._build_main_menu_map()
            selection = self.ui.show_menu("Todos", list(menu_map.keys()))
            if not selection:
                break
            action = menu_map.get(selection)
            if action:
                action()

    def _build_main_menu_map(self) -> dict[str, Callable[[], None]]:
        mapping: dict[str, Callable[[], None]] = {}
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

    # ------------------------------------------------------------------
    # Item actions
    # ------------------------------------------------------------------

    def handle_item_actions(self, item: TodoItem) -> None:
        options: list[str] = [
            "Toggle Done",
            "Display",
            "Edit Text",
            "Edit Date",
            "Manage Open Items",
            "Delete",
            "Archive",
            "Back",
        ]
        if item.environment is not None:
            options.insert(-1, "Open Environment")
            options.insert(-1, "Clear Environment")
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
        elif choice == "Clear Environment":
            if item.environment is None:
                return
            item.environment = None
            self.store.update_todo(item)
        elif choice == "Open Environment":
            if item.environment:
                launch.launch_environment(item.environment)
        elif choice == "Manage Open Items":
            if item.environment is None:
                item.environment = Environment()
            self._manage_open_items(item)

    def _manage_open_items(self, item: TodoItem) -> None:
        """Menu for adding, removing, and listing OpenItem entries."""
        if item.environment is None:
            return

        while True:
            options: list[str] = ["+ Add Open Item", "+ Add from directory", "Back"]
            opens = item.environment.opens

            for idx, oi in enumerate(opens):
                path_display = oi.path if oi.path else "(no target)"
                label = f"{idx + 1}. [{oi.app.value}] {path_display}"
                options.insert(-2, f"Remove {label}")

            choice = self.ui.show_menu("Open Items", options)
            if not choice or choice == "Back":
                return

            if choice == "+ Add Open Item":
                self._add_open_item(item)
            elif choice == "+ Add from directory":
                self._add_directory_items(item)
            elif choice.startswith("Remove "):
                target_label = choice[len("Remove "):]
                # Extract the index from "1. [app] path"
                try:
                    num = int(target_label.split(".")[0])
                except (ValueError, IndexError):
                    continue
                if 0 < num <= len(opens):
                    opens.pop(num - 1)
                    self.store.update_todo(item)

    def _add_open_item(self, item: TodoItem) -> None:
        """Prompt for path and app to add an OpenItem."""
        if item.environment is None:
            return

        path_raw = self.ui.ask_text("Path / URL to open (leave empty to just launch app)")
        if path_raw is None:
            return

        resolved: str | None = None
        if path_raw.strip():
            resolved = self._resolve_env_path(path_raw)
            if not resolved:
                return

        app_labels = [a.value for a in AppLauncher]
        selection = self.ui.show_menu(
            "Select app",
            app_labels,
        )
        if not selection:
            return

        app = AppLauncher.from_string(selection)

        if not resolved and not app.can_launch_alone():
            return

        item.environment.opens.append(OpenItem(app=app, path=resolved))
        self.store.update_todo(item)

    def _add_directory_items(self, item: TodoItem) -> None:
        """Add all files from a directory as OpenItems with a single app."""
        if item.environment is None:
            return

        dir_raw = self.ui.ask_text("Directory to scan")
        if dir_raw is None or not dir_raw.strip():
            return

        resolved = self._resolve_env_path(dir_raw)
        dir_path = Path(resolved)
        if not dir_path.is_dir():
            return

        files = sorted(str(f) for f in dir_path.iterdir() if f.is_file())
        if not files:
            return

        app_labels = [a.value for a in AppLauncher]
        selection = self.ui.show_menu(
            "Select app for directory files",
            app_labels,
        )
        if not selection:
            return

        app = AppLauncher.from_string(selection)
        for fpath in files:
            item.environment.opens.append(OpenItem(path=fpath, app=app))
        self.store.update_todo(item)

    # ------------------------------------------------------------------
    # Archive menu
    # ------------------------------------------------------------------

    def show_archive_menu(self) -> None:
        while True:
            archived = self.store.get_archived_items()
            if not archived:
                self.ui.show_menu("Archived", ["(empty)", "Back"])
                return

            mapping: dict[str, Callable[[], None]] = {"Back": lambda: None}
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

    # ------------------------------------------------------------------
    # Long-term menu
    # ------------------------------------------------------------------

    def show_long_term_menu(self) -> None:
        while True:
            items = self.store.get_long_term()
            mapping: dict[str, Callable[[], None]] = {
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
    positional = [a for a in sys.argv[1:] if not a.startswith("-")]
    path_arg = positional[0] if positional else str(default_data_path())
    db_path = Path(path_arg).expanduser()
    if not db_path.is_absolute():
        db_path = resolve_path(str(db_path), module_root())

    store = TodoStore(db_path)
    store.ensure_file()
    app = TodoApp(store, RofiUI())

    if "--set-environment" in sys.argv:
        item = display.get_display_item(store)
        if item is None:
            return
        todo = TodoItem.from_dict(item)

        if todo.environment is None:
            todo.environment = Environment()
            store.update_todo(todo)

        # Open the manage open items screen.
        app._manage_open_items(todo)
    else:
        app.run()


if __name__ == "__main__":
    main()
