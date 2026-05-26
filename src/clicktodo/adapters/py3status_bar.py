# -*- coding: utf-8 -*-
"""py3status module implementation for the status bar."""

from __future__ import annotations

import shutil
import subprocess

from clicktodo import display
from clicktodo.launch import spawn_ui
from clicktodo.models import TodoItem
from clicktodo.paths import default_data_path, module_root, resolve_path
from clicktodo.store import TodoStore


class Py3status:
    data_path = ""
    format = "✅ {done}/{total} • {next}"
    max_width = 40
    refresh_seconds = 5
    ui_via_i3 = True
    ui_command = ""

    _store: TodoStore | None = None

    def post_config_hook(self):
        path = self.data_path.strip() if self.data_path else str(default_data_path())
        self._store = TodoStore(resolve_path(path, module_root()))
        self._store.ensure_file()

    @property
    def store(self) -> TodoStore:
        if self._store is None:
            self.post_config_hook()
        return self._store  # type: ignore[return-value]

    def clicktodo(self):
        self.store.reload()
        done, total = display.todo_counts(self.store.data)
        text = display.next_label(self.store, self.max_width)
        return {
            "full_text": self.py3.safe_format(
                self.format,
                {"done": done, "total": total, "next": text},
            ),
            "cached_until": self.py3.time_in(self.refresh_seconds),
        }

    def on_click(self, event):
        button = event["button"]
        store = self.store
        store.reload()

        if button == 1:
            self._launch_ui()
            return

        if button == 2:
            display.mark_displayed_done(store)
        elif button == 3:
            raw_item = display.get_display_item(store)
            if raw_item is not None and shutil.which("code"):
                todo = TodoItem.from_dict(raw_item)
                if todo.environment and todo.environment.path:
                    subprocess.Popen(
                        ["code", "--reuse-window", todo.environment.path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
        elif button == 4:
            display.cycle_display(store, -1)
        elif button == 5:
            display.cycle_display(store, 1)

    def _launch_ui(self):
        spawn_ui(
            self.store.filepath,
            via_i3=self.ui_via_i3,
            custom_command=self.ui_command,
        )
