"""Tests for UI launch helpers."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from clicktodo import launch


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
