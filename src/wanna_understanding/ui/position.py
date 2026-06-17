# SPDX-License-Identifier: AGPL-3.0

"""悬浮窗定位计算（纯函数，便于测试）。"""

from __future__ import annotations


def compute_overlay_position(
    window_rect: tuple[int, int, int, int],
    overlay_width: int,
    overlay_height: int,
    screen_width: int,
    screen_height: int,
    margin: int = 10,
) -> tuple[int, int]:
    """计算悬浮窗左上角坐标，右侧放不下时翻到目标窗口左侧。"""
    left, top, right, _bottom = window_rect
    x = right + margin
    if x + overlay_width > screen_width:
        x = max(margin, left - overlay_width - margin)
    y = max(margin, min(top, screen_height - overlay_height - margin))
    return x, y
