# SPDX-License-Identifier: AGPL-3.0

"""全局快捷键检测（Windows）。"""

from __future__ import annotations

import sys


def hotkey_toggle_pressed() -> bool:
    """检测 Ctrl+Shift+H 是否被按下（边沿触发由调用方处理）。"""
    if sys.platform != "win32":
        return False
    import ctypes

    user32 = ctypes.windll.user32
    ctrl = user32.GetAsyncKeyState(0x11) & 0x8000
    shift = user32.GetAsyncKeyState(0x10) & 0x8000
    key = user32.GetAsyncKeyState(0x48) & 0x8000  # H
    return bool(ctrl and shift and key)
