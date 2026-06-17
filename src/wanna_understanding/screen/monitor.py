# SPDX-License-Identifier: AGPL-3.0

"""多显示器工作区工具。"""

from __future__ import annotations

import sys

if sys.platform == "win32":
    import win32api
    import win32con
else:
    win32api = None  # type: ignore[assignment]
    win32con = None  # type: ignore[assignment]


def get_work_area_for_rect(
    window_rect: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    """获取包含窗口中心点的显示器工作区 (left, top, right, bottom)。"""
    if win32api is None or win32con is None:
        left, top, right, bottom = window_rect
        return left, top, right + 1920, bottom + 1080
    center_x = (window_rect[0] + window_rect[2]) // 2
    center_y = (window_rect[1] + window_rect[3]) // 2
    monitor = win32api.MonitorFromPoint(
        (center_x, center_y),
        win32con.MONITOR_DEFAULTTONEAREST,
    )
    info = win32api.GetMonitorInfo(monitor)
    work = info["Work"]
    return int(work[0]), int(work[1]), int(work[2]), int(work[3])
