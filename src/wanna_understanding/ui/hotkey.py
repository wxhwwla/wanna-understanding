# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

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


def _alt_shift_key_pressed(vk_code: int) -> bool:
    """检测 Alt+Shift+指定虚拟键是否按下。"""
    if sys.platform != "win32":
        return False
    import ctypes

    user32 = ctypes.windll.user32
    alt = user32.GetAsyncKeyState(0x12) & 0x8000  # VK_MENU
    shift = user32.GetAsyncKeyState(0x10) & 0x8000
    key = user32.GetAsyncKeyState(vk_code) & 0x8000
    return bool(alt and shift and key)


def hotkey_toggle_pressed() -> bool:
    """Alt+Shift+H — 显示/隐藏悬浮窗。"""
    return _alt_shift_key_pressed(0x48)


def hotkey_history_pressed() -> bool:
    """Alt+Shift+J — 打开分析历史。"""
    return _alt_shift_key_pressed(0x4A)


def hotkey_settings_pressed() -> bool:
    """Alt+Shift+S 或 Alt+Shift+O — 打开设置。"""
    return _alt_shift_key_pressed(0x53) or _alt_shift_key_pressed(0x4F)


def hotkey_freeze_pressed() -> bool:
    """Alt+Shift+F — 冻结/解冻悬浮窗内容（避免 Ctrl 系列冲突）。"""
    return _alt_shift_key_pressed(0x46)
