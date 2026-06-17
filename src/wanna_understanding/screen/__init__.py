# SPDX-License-Identifier: AGPL-3.0

"""屏幕捕获模块。"""

from .capture_plan import (
    build_monitor_region,
    crop_ratio_for_title,
    should_strip_line_numbers,
)
from .capturer import ScreenCapturer
from .custom_region import ScreenRect, format_monitor_rect, parse_monitor_rect
from .monitor import get_work_area_for_rect
from .region import WindowRegion
from .window import (
    get_dpi_scale,
    get_foreground_window_info,
    get_window_client_region,
    is_window_visible,
)

__all__ = [
    "ScreenCapturer",
    "ScreenRect",
    "WindowRegion",
    "build_monitor_region",
    "crop_ratio_for_title",
    "format_monitor_rect",
    "get_dpi_scale",
    "get_foreground_window_info",
    "get_window_client_region",
    "get_work_area_for_rect",
    "is_window_visible",
    "parse_monitor_rect",
    "should_strip_line_numbers",
]
