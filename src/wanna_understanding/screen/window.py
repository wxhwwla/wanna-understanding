# SPDX-License-Identifier: AGPL-3.0

"""Windows 窗口工具：活动窗口、客户区矩形与 DPI 缩放。"""

from __future__ import annotations

import ctypes
import sys

from .region import WindowRegion

if sys.platform == "win32":
    import win32gui
else:
    win32gui = None  # type: ignore[assignment]


def _require_win32() -> None:
    if win32gui is None:
        msg = "屏幕捕获仅支持 Windows 平台"
        raise OSError(msg)


def get_dpi_scale(hwnd: int) -> float:
    """获取目标窗口的 DPI 缩放比例。"""
    _require_win32()
    try:
        dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)  # type: ignore[attr-defined]
        return dpi / 96.0
    except (AttributeError, OSError):
        return 1.0


def get_foreground_window_info() -> tuple[int, str]:
    """获取当前活动窗口的句柄与标题。"""
    _require_win32()
    hwnd = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(hwnd)
    return hwnd, title


def is_window_visible(hwnd: int) -> bool:
    """判断窗口是否可见且未最小化。"""
    _require_win32()
    if not hwnd or not win32gui.IsWindow(hwnd):
        return False
    return bool(win32gui.IsWindowVisible(hwnd)) and not win32gui.IsIconic(hwnd)


def get_window_client_region(hwnd: int) -> WindowRegion:
    """获取窗口客户区在屏幕上的区域。"""
    _require_win32()
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    screen_left, screen_top = win32gui.ClientToScreen(hwnd, (left, top))
    width = max(1, right - left)
    height = max(1, bottom - top)
    return WindowRegion(
        hwnd=hwnd,
        x=screen_left,
        y=screen_top,
        width=width,
        height=height,
        dpi_scale=get_dpi_scale(hwnd),
    )
