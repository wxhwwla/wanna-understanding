# SPDX-License-Identifier: AGPL-3.0

"""全局快捷键检测（Windows）。"""

from __future__ import annotations

import sys


def _ctrl_shift_key_pressed(vk_code: int) -> bool:
    """检测 Ctrl+Shift+指定虚拟键是否按下。"""
    if sys.platform != "win32":
        return False
    import ctypes

    user32 = ctypes.windll.user32
    ctrl = user32.GetAsyncKeyState(0x11) & 0x8000
    shift = user32.GetAsyncKeyState(0x10) & 0x8000
    key = user32.GetAsyncKeyState(vk_code) & 0x8000
    return bool(ctrl and shift and key)


def hotkey_toggle_pressed() -> bool:
    """Ctrl+Shift+H — 显示/隐藏悬浮窗。"""
    return _ctrl_shift_key_pressed(0x48)


def hotkey_history_pressed() -> bool:
    """Ctrl+Shift+J — 打开分析历史。"""
    return _ctrl_shift_key_pressed(0x4A)


def hotkey_settings_pressed() -> bool:
    """Ctrl+Shift+S 或 Ctrl+Shift+O — 打开设置。"""
    return _ctrl_shift_key_pressed(0x53) or _ctrl_shift_key_pressed(0x4F)
