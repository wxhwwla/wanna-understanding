# SPDX-License-Identifier: AGPL-3.0

"""自定义屏幕监控区域解析。"""

from __future__ import annotations

from dataclasses import dataclass

from .region import WindowRegion


@dataclass(frozen=True, slots=True)
class ScreenRect:
    """屏幕绝对坐标矩形。"""

    x: int
    y: int
    width: int
    height: int

    def to_region(self, hwnd: int = 0) -> WindowRegion:
        """转换为 WindowRegion（自定义区域无 DPI 缩放）。"""
        return WindowRegion(
            hwnd=hwnd,
            x=self.x,
            y=self.y,
            width=max(1, self.width),
            height=max(1, self.height),
            dpi_scale=1.0,
        )


def parse_monitor_rect(raw: str) -> ScreenRect | None:
    """解析 `left,top,width,height` 格式的监控矩形。"""
    text = raw.strip()
    if not text:
        return None
    parts = [part.strip() for part in text.split(",")]
    if len(parts) != 4:
        return None
    try:
        left, top, width, height = (int(part) for part in parts)
    except ValueError:
        return None
    if width < 1 or height < 1:
        return None
    return ScreenRect(x=left, y=top, width=width, height=height)


def format_monitor_rect(rect: ScreenRect) -> str:
    """格式化为环境变量字符串。"""
    return f"{rect.x},{rect.y},{rect.width},{rect.height}"
