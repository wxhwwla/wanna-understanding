# SPDX-License-Identifier: AGPL-3.0

"""区域值对象：封装矩形坐标并处理 DPI 缩放与中心裁剪。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WindowRegion:
    """窗口或屏幕上的矩形区域。"""

    hwnd: int
    x: int
    y: int
    width: int
    height: int
    dpi_scale: float = 1.0

    def physical_rect(self) -> tuple[int, int, int, int]:
        """返回物理像素截图区域 (left, top, width, height)。

        x/y 来自 ClientToScreen，已是物理坐标；宽高为逻辑客户区尺寸，需乘 DPI。
        """
        return (
            self.x,
            self.y,
            max(1, int(self.width * self.dpi_scale)),
            max(1, int(self.height * self.dpi_scale)),
        )

    def strip_line_numbers(self, left_ratio: float = 0.06) -> WindowRegion:
        """裁掉左侧行号区域（默认 6% 宽度）。"""
        left_ratio = max(0.0, min(left_ratio, 0.3))
        strip = max(0, int(self.width * left_ratio))
        if strip <= 0 or strip >= self.width:
            return self
        return WindowRegion(
            hwnd=self.hwnd,
            x=self.x + strip,
            y=self.y,
            width=self.width - strip,
            height=self.height,
            dpi_scale=self.dpi_scale,
        )

    def center_crop(self, ratio: float = 0.7) -> WindowRegion:
        """裁剪中间 ratio 比例的区域，过滤行号与状态栏。"""
        ratio = max(0.1, min(ratio, 1.0))
        crop_w = max(1, int(self.width * ratio))
        crop_h = max(1, int(self.height * ratio))
        offset_x = (self.width - crop_w) // 2
        offset_y = (self.height - crop_h) // 2
        return WindowRegion(
            hwnd=self.hwnd,
            x=self.x + offset_x,
            y=self.y + offset_y,
            width=crop_w,
            height=crop_h,
            dpi_scale=self.dpi_scale,
        )

    def as_monitor_dict(self) -> dict[str, int]:
        """转换为 mss 截图所需的 monitor 字典（屏幕物理像素）。"""
        left, top, width, height = self.physical_rect()
        return {"left": left, "top": top, "width": width, "height": height}
