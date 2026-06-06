"""Tests for UI launch helpers."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from clicktodo import launch
from clicktodo.models import AppLauncher, Environment, OpenItem


def test_ui_command_prefers_clicktodo_ui(tmp_path):
    data = tmp_path / "todos.json"
    data.write_text("{}", encoding="utf-8")
    with patch.object(launch.shutil, "which", return_value="/usr/bin/clicktodo-ui"):
        argv = launch.ui_command(data)
    assert argv == ["/usr/bin/clicktodo-ui", str(data.resolve())]


def test_ui_command_falls_back_to_module(tmp_path):
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


def test_ui_command_custom_override(tmp_path):
    data = tmp_path / "todos.json"
    data.write_text("{}", encoding="utf-8")
    argv = launch.ui_command(data, custom_command="my-ui --foo")
    assert argv == ["my-ui", "--foo", str(data.resolve())]


def test_spawn_ui_wraps_with_i3_msg(tmp_path):
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
    assert argv[:5] == [
        "i3-msg",
        "-q",
        "exec",
        "--",
        "/usr/bin/clicktodo-ui",
    ]
    assert argv[5] == str(data.resolve())


def test_spawn_ui_direct_when_no_i3_msg(tmp_path):
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


def test_set_environment_flag_not_misused_as_path(tmp_path):
    """Regression: --set-environment should not be used as the todos.json path."""
    from clicktodo.adapters.rofi import app as rofi_app

    data = tmp_path / "todos.json"
    data.write_text('{"todos":[],"archived":[],"long-term":[],"display_id":0,"seq":0}', encoding="utf-8")

    mock_ui = MagicMock()
    mock_ui.ask_text.return_value = None
    mock_ui.show_menu.return_value = "Back"  # exits manage loop

    with patch.object(rofi_app.sys, "argv", ["clicktodo-ui", "--set-environment", str(data)]):
        with patch.object(rofi_app, "RofiUI", return_value=mock_ui):
            rofi_app.main()

    assert data.exists()


# ---------------------------------------------------------------------------
# App launcher dispatch
# ---------------------------------------------------------------------------


def test_launch_command_firefox(tmp_path):
    data = tmp_path / "page.html"
    data.write_text("<html></html>", encoding="utf-8")

    def which(name):
        return "/usr/bin/firefox" if name == "firefox" else None

    with patch.object(launch.shutil, "which", side_effect=which):
        cmd = launch._launch_command(AppLauncher.FIREFOX, str(data))
    assert cmd == ["firefox", "--new-tab", str(data)]


def test_launch_command_code(tmp_path):
    data = tmp_path / "main.py"
    data.write_text("print(1)", encoding="utf-8")

    def which(name):
        return "/usr/bin/code" if name == "code" else None

    with patch.object(launch.shutil, "which", side_effect=which):
        cmd = launch._launch_command(AppLauncher.CODE, str(data))
    assert cmd == ["code", "--reuse-window", str(data)]


def test_launch_command_cursor(tmp_path):
    data = tmp_path / "main.py"

    def which(name):
        return "/usr/bin/cursor" if name == "cursor" else None

    with patch.object(launch.shutil, "which", side_effect=which):
        cmd = launch._launch_command(AppLauncher.CURSOR, str(data))
    assert cmd == ["cursor", str(data)]


def test_launch_command_okular(tmp_path):
    data = tmp_path / "doc.pdf"

    def which(name):
        return "/usr/bin/okular" if name == "okular" else None

    with patch.object(launch.shutil, "which", side_effect=which):
        cmd = launch._launch_command(AppLauncher.OKULAR, str(data))
    assert cmd == ["okular", str(data)]


def test_launch_command_not_found_returns_none():
    def which(name):
        return None

    with patch.object(launch.shutil, "which", side_effect=which):
        cmd = launch._launch_command(AppLauncher.FIREFOX, "/tmp/x")
    assert cmd is None


def test_launch_command_remnote():
    """REMNOTE maps to RemNote.AppImage in PATH."""

    def which(name):
        return "/opt/RemNote.AppImage" if name == "RemNote.AppImage" else None

    with patch.object(launch.shutil, "which", side_effect=which):
        cmd = launch._launch_command(AppLauncher.REMNOTE, "/tmp/note")
    assert cmd == ["RemNote.AppImage", "/tmp/note"]


def test_launch_command_remnote_not_found():
    """REMNOTE returns None when RemNote.AppImage is not in PATH."""

    def which(name):
        return None

    with patch.object(launch.shutil, "which", side_effect=which):
        cmd = launch._launch_command(AppLauncher.REMNOTE, "/tmp/note")
    assert cmd is None


def test_launch_open_item_spawns_process(tmp_path):
    data = tmp_path / "main.py"
    item = OpenItem(path=str(data), app=AppLauncher.CODE)

    def which(name):
        return "/usr/bin/code" if name == "code" else None

    mock_popen = MagicMock()
    with patch.object(launch.shutil, "which", side_effect=which):
        with patch.object(launch.subprocess, "Popen", mock_popen):
            launch.launch_open_item(item)

    mock_popen.assert_called_once()
    argv = mock_popen.call_args[0][0]
    assert argv[0] == "code"


def test_launch_environment_with_opens(tmp_path):
    env = Environment(
        opens=[
            OpenItem(path=str(tmp_path / "doc.pdf"), app=AppLauncher.OKULAR),
            OpenItem(path=str(tmp_path / "main.py"), app=AppLauncher.CODE),
        ],
    )

    def which(name):
        if name == "okular":
            return "/usr/bin/okular"
        if name == "code":
            return "/usr/bin/code"
        return None

    mock_popen = MagicMock()
    with patch.object(launch.shutil, "which", side_effect=which):
        with patch.object(launch.subprocess, "Popen", mock_popen):
            launch.launch_environment(env)

    # Should have spawned 2 processes.
    assert mock_popen.call_count == 2


def test_launch_environment_empty_noop():
    """When opens is empty, launch_environment does nothing."""
    env = Environment()

    mock_popen = MagicMock()
    with patch.object(launch.subprocess, "Popen", mock_popen):
        launch.launch_environment(env)

    mock_popen.assert_not_called()


# ---------------------------------------------------------------------------
# Pathless OpenItem (launch-only mode)
# ---------------------------------------------------------------------------


def test_launch_firefox_without_target():
    """Firefox launches without --new-tab when no target."""

    def which(name):
        return "/usr/bin/firefox" if name == "firefox" else None

    with patch.object(launch.shutil, "which", side_effect=which):
        cmd = launch._launch_command(AppLauncher.FIREFOX, None)
    assert cmd == ["firefox"]


def test_launch_remnote_without_target():
    """RemNote launches without a target arg."""

    def which(name):
        return "/opt/RemNote.AppImage" if name == "RemNote.AppImage" else None

    with patch.object(launch.shutil, "which", side_effect=which):
        cmd = launch._launch_command(AppLauncher.REMNOTE, None)
    assert cmd == ["RemNote.AppImage"]


def test_launch_code_requires_target():
    """Code returns None when no target is provided."""

    def which(name):
        return "/usr/bin/code" if name == "code" else None

    with patch.object(launch.shutil, "which", side_effect=which):
        cmd = launch._launch_command(AppLauncher.CODE, None)
    assert cmd is None


def test_launch_cursor_requires_target():
    """Cursor returns None when no target is provided."""

    def which(name):
        return "/usr/bin/cursor" if name == "cursor" else None

    with patch.object(launch.shutil, "which", side_effect=which):
        cmd = launch._launch_command(AppLauncher.CURSOR, None)
    assert cmd is None


def test_launch_okular_requires_target():
    """Okular returns None when no target is provided."""

    def which(name):
        return "/usr/bin/okular" if name == "okular" else None

    with patch.object(launch.shutil, "which", side_effect=which):
        cmd = launch._launch_command(AppLauncher.OKULAR, None)
    assert cmd is None


def test_launch_open_item_pathless_spawns_process():
    """Pathless OpenItem spawns the app without a target arg."""
    item = OpenItem(app=AppLauncher.FIREFOX)

    def which(name):
        return "/usr/bin/firefox" if name == "firefox" else None

    mock_popen = MagicMock()
    with patch.object(launch.shutil, "which", side_effect=which):
        with patch.object(launch.subprocess, "Popen", mock_popen):
            launch.launch_open_item(item)

    mock_popen.assert_called_once()
    assert mock_popen.call_args[0][0] == ["firefox"]


def test_launch_open_item_pathless_not_supported():
    """Pathless OpenItem for non-launch-only apps is a no-op."""
    item = OpenItem(app=AppLauncher.CODE)

    mock_popen = MagicMock()
    with patch.object(launch.subprocess, "Popen", mock_popen):
        launch.launch_open_item(item)

    mock_popen.assert_not_called()
