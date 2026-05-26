"""Edge-case tests for clicktodo.launch, paths, notify, and rofi/ui."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from clicktodo import launch, notify, paths
from clicktodo.adapters.rofi.ui import RofiUI
from tests.mock.ui import MockUI


# ---------------------------------------------------------------------------
# launch.py
# ---------------------------------------------------------------------------


class TestUICommand:
    def test_prefers_clicktodo_ui(self, tmp_path: Path):
        data = tmp_path / "todos.json"
        data.write_text("{}", encoding="utf-8")
        with patch.object(launch.shutil, "which", return_value="/usr/bin/clicktodo-ui"):
            argv = launch.ui_command(data)
        assert argv == ["/usr/bin/clicktodo-ui", str(data.resolve())]

    def test_falls_back_to_module(self, tmp_path: Path):
        data = tmp_path / "todos.json"
        data.write_text("{}", encoding="utf-8")
        with patch.object(launch.shutil, "which", return_value=None):
            argv = launch.ui_command(data)
        assert argv == [
            sys.executable,
            "-m",
            "clicktodo.adapters.rofi.app",
            str(data.resolve()),
        ]

    def test_custom_command_override(self, tmp_path: Path):
        data = tmp_path / "todos.json"
        data.write_text("{}", encoding="utf-8")
        argv = launch.ui_command(data, custom_command="my-ui --foo")
        assert argv == ["my-ui", "--foo", str(data.resolve())]

    def test_empty_custom_command_uses_default(self, tmp_path: Path):
        """Whitespace-only custom_command should behave like empty string."""
        data = tmp_path / "todos.json"
        data.write_text("{}", encoding="utf-8")
        with patch.object(launch.shutil, "which", return_value="/usr/bin/clicktodo-ui"):
            argv = launch.ui_command(data, custom_command="  ")
        assert argv[0] == "/usr/bin/clicktodo-ui"

    def test_shell_injection_escaped_in_custom_command(self, tmp_path: Path):
        """shlex.split should prevent shell injection."""
        data = tmp_path / "todos.json"
        data.write_text("{}", encoding="utf-8")
        argv = launch.ui_command(data, custom_command='"; rm -rf /"')
        # shlex.split handles this; result should be safe tokens, not shell commands.
        assert ";" not in argv
        assert "rm" not in argv or argv[0] == '"'


# ---------------------------------------------------------------------------
# spawn_ui
# ---------------------------------------------------------------------------


class TestSpawnUI:
    def test_wraps_with_i3_msg(self, tmp_path: Path):
        data = tmp_path / "todos.json"
        data.write_text("{}", encoding="utf-8")

        def which(name):
            if name == "i3-msg":
                return "/usr/bin/i3-msg"
            if name == "clicktodo-ui":
                return "/usr/bin/clicktodo-ui"
            return None

        mock_popen = MagicMock()
        with patch.object(launch.shutil, "which", side_effect=which):
            with patch.object(launch.subprocess, "Popen", mock_popen):
                launch.spawn_ui(data, via_i3=True)

        mock_popen.assert_called_once()
        argv = mock_popen.call_args[0][0]
        assert argv[:5] == ["i3-msg", "-q", "exec", "--", "/usr/bin/clicktodo-ui"]

    def test_direct_when_no_i3_msg(self, tmp_path: Path):
        data = tmp_path / "todos.json"
        data.write_text("{}", encoding="utf-8")

        def which(name):
            return "/usr/bin/clicktodo-ui" if name == "clicktodo-ui" else None

        mock_popen = MagicMock()
        with patch.object(launch.shutil, "which", side_effect=which):
            with patch.object(launch.subprocess, "Popen", mock_popen):
                launch.spawn_ui(data, via_i3=True)

        argv = mock_popen.call_args[0][0]
        assert argv[0] == "/usr/bin/clicktodo-ui"
        assert mock_popen.call_args[1]["start_new_session"] is True

    def test_via_i3_false_always_direct(self, tmp_path: Path):
        data = tmp_path / "todos.json"
        data.write_text("{}", encoding="utf-8")

        def which(name):
            if name == "i3-msg":
                return "/usr/bin/i3-msg"
            if name == "clicktodo-ui":
                return "/usr/bin/clicktodo-ui"
            return None

        mock_popen = MagicMock()
        with patch.object(launch.shutil, "which", side_effect=which):
            with patch.object(launch.subprocess, "Popen", mock_popen):
                launch.spawn_ui(data, via_i3=False)

        argv = mock_popen.call_args[0][0]
        assert "i3-msg" not in argv

    def test_debug_log_creation(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Debug mode should create a log file."""
        data = tmp_path / "todos.json"
        data.write_text("{}", encoding="utf-8")
        monkeypatch.setenv("CLICKTODO_DEBUG", "1")
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))

        def which(name):
            if name == "clicktodo-ui":
                return "/usr/bin/clicktodo-ui"
            return None

        mock_popen = MagicMock()
        with patch.object(launch.shutil, "which", side_effect=which):
            with patch.object(launch.subprocess, "Popen", mock_popen):
                launch.spawn_ui(data, via_i3=False)

        log_path = tmp_path / "xdg" / "clicktodo" / "launch.log"
        assert log_path.exists()
        assert "spawn_ui" in log_path.read_text()


# ---------------------------------------------------------------------------
# paths.py
# ---------------------------------------------------------------------------


class TestPaths:
    def test_module_root_returns_path(self):
        root = paths.module_root()
        assert root.is_dir()

    def test_default_data_path_no_xdg(self, no_xdg_env):
        result = paths.default_data_path()
        assert result.parts[-4:] == (".local", "share", "clicktodo", "todos.json")

    def test_default_data_path_with_custom_xdg(self, custom_xdg):
        result = paths.default_data_path()
        assert str(custom_xdg) in str(result)
        assert result.name == "todos.json"

    def test_resolve_path_absolute(self):
        result = paths.resolve_path("/tmp/test.json")
        assert result == Path("/tmp/test.json")

    def test_resolve_path_relative_to_module_root(self):
        result = paths.resolve_path("data/todos.json")
        assert result.is_absolute()
        assert result.name == "todos.json"

    def test_resolve_path_with_custom_base(self, tmp_path: Path):
        result = paths.resolve_path("foo.json", base=tmp_path)
        assert result == tmp_path / "foo.json"

    def test_resolve_path_tilde_expanded(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("HOME", "/fake/home")
        result = paths.resolve_path("~/config.json")
        assert str(result).startswith("/fake/home")


# ---------------------------------------------------------------------------
# notify.py
# ---------------------------------------------------------------------------


class TestNotify:
    def test_no_op_when_py3cmd_missing(self):
        with patch.object(notify.shutil, "which", return_value=None):
            # Should not raise.
            notify.refresh_status_bar()

    def test_runs_py3cmd_when_available(self):
        mock_run = MagicMock()
        with patch.object(notify.shutil, "which", return_value="/usr/bin/py3-cmd"):
            with patch.object(notify.subprocess, "run", mock_run):
                notify.refresh_status_bar()
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args == ["py3-cmd", "refresh", "clicktodo"]

    def test_py3cmd_failure_ignored(self):
        mock_run = MagicMock(return_value=MagicMock(returncode=1))
        with patch.object(notify.shutil, "which", return_value="/usr/bin/py3-cmd"):
            with patch.object(notify.subprocess, "run", mock_run):
                # Should not raise even if py3-cmd fails.
                notify.refresh_status_bar()


# ---------------------------------------------------------------------------
# rofi/ui.py  (RofiUI protocol conformance)
# ---------------------------------------------------------------------------


class TestRofiUIProtocol:
    def test_rofi_ui_conforms_to_protocol(self):
        """RofiUI implements UIBackend methods."""
        ui = RofiUI()
        assert hasattr(ui, "show_menu")
        assert hasattr(ui, "ask_text")

    def test_mock_ui_conforms_to_protocol(self):
        ui = MockUI()
        ui.queue_menu_response("opt1")
        assert ui.show_menu("test", ["opt1", "opt2"]) == "opt1"
        ui.queue_text_response("hello")
        assert ui.ask_text("prompt") == "hello"
