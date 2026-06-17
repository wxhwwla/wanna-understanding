# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""悬浮窗定位计算（纯函数，便于测试）。"""

from __future__ import annotations


def compute_overlay_position(
    window_rect: tuple[int, int, int, int],
    overlay_width: int,
    overlay_height: int,
    work_area: tuple[int, int, int, int],
    margin: int = 10,
) -> tuple[int, int]:
    """在显示器工作区内计算悬浮窗左上角坐标。"""
    wa_left, wa_top, wa_right, wa_bottom = work_area
    left, top, right, _bottom = window_rect
    x = right + margin
    if x + overlay_width > wa_right:
        x = max(wa_left + margin, left - overlay_width - margin)
    y = max(wa_top + margin, min(top, wa_bottom - overlay_height - margin))
    return x, y
