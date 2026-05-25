# -*- coding: utf-8 -*-
"""
py3status module — symlink into ~/.config/py3status/modules/clicktodo.py

py3status loads this file as module name "clicktodo", which shadows the real
package. Pop that binding, import from src/ (or site-packages), then expose
Py3status on this module object.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

_shim = sys.modules.pop(__name__, None)
try:
    _bar = importlib.import_module("clicktodo.adapters.py3status_bar")
finally:
    if _shim is not None:
        sys.modules[__name__] = _shim

Py3status = _bar.Py3status
if _shim is not None:
    _shim.Py3status = Py3status

__all__ = ["Py3status"]
