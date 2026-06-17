# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""根据配置与窗口信息计算截图区域。"""

from __future__ import annotations

from wanna_understanding.ocr.profiles import get_profile
from wanna_understanding.screen.custom_region import parse_monitor_rect
from wanna_understanding.screen.region import WindowRegion
from wanna_understanding.screen.window import get_window_client_region


def crop_ratio_for_title(
    title: str,
    *,
    default_ratio: float,
    editor_profile: str = "auto",
) -> float:
    """按编辑器类型返回中心裁剪比例。"""
    if editor_profile != "auto":
        return get_profile(editor_profile).resolve_crop_ratio(default_ratio)
    lowered = title.casefold()
    if "pycharm" in lowered or "intellij" in lowered:
        return 0.68
    if "visual studio code" in lowered or "cursor" in lowered:
        return 0.72
    return default_ratio


def should_strip_line_numbers(title: str, *, editor_profile: str = "auto") -> bool:
    """是否裁掉左侧行号列。"""
    if editor_profile != "auto":
        return get_profile(editor_profile).strip_line_numbers
    lowered = title.casefold()
    return "pycharm" in lowered or "intellij" in lowered


def build_monitor_region(
    hwnd: int,
    title: str,
    *,
    monitor_mode: str,
    monitor_rect: str,
    crop_ratio: float,
    editor_profile: str = "auto",
) -> WindowRegion:
    """构建本次截图使用的屏幕区域。"""
    if monitor_mode == "custom":
        rect = parse_monitor_rect(monitor_rect)
        if rect is not None:
            return rect.to_region(hwnd=0)
    region = get_window_client_region(hwnd)
    region = region.center_crop(
        crop_ratio_for_title(
            title,
            default_ratio=crop_ratio,
            editor_profile=editor_profile,
        )
    )
    if should_strip_line_numbers(title, editor_profile=editor_profile):
        region = region.strip_line_numbers()
    return region
