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
        """返回 DPI 补偿后的物理像素坐标 (left, top, width, height)。"""
        scale = self.dpi_scale
        return (
            int(self.x * scale),
            int(self.y * scale),
            max(1, int(self.width * scale)),
            max(1, int(self.height * scale)),
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
        """转换为 mss 截图所需的 monitor 字典。"""
        left, top, width, height = self.physical_rect()
        return {"left": left, "top": top, "width": width, "height": height}
