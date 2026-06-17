# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""屏幕截图引擎：基于 mss 截取全屏或指定区域。"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import mss
from PIL import Image

from .region import WindowRegion
from .window import get_window_client_region, is_window_visible

if TYPE_CHECKING:
    from collections.abc import Callable


class ScreenCapturer:
    """截图抽象层，默认使用 mss 实现。"""

    def __init__(self, mss_factory: Callable[[], mss.mss] | None = None) -> None:
        self._mss_factory = mss_factory or mss.mss

    def capture(self, region: WindowRegion | None = None) -> Image.Image:
        """截取指定区域；region 为 None 时截取主显示器全屏。"""
        with self._mss_factory() as sct:
            monitor = sct.monitors[1] if region is None else region.as_monitor_dict()
            shot = sct.grab(monitor)
            return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

    def capture_window(self, hwnd: int) -> Image.Image:
        """截取指定窗口句柄的客户区。"""
        if not is_window_visible(hwnd):
            msg = f"窗口不可见或已最小化: hwnd={hwnd}"
            raise ValueError(msg)
        region = get_window_client_region(hwnd)
        return self.capture(region)

    @staticmethod
    def hash_image(image: Image.Image) -> str:
        """计算截图内容的 SHA256 哈希，用于变化检测（缩小后降低 UI 微动敏感度）。"""
        sample = image.resize((64, 64), Image.Resampling.LANCZOS).convert("L")
        return hashlib.sha256(sample.tobytes()).hexdigest()
