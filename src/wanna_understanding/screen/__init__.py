# SPDX-License-Identifier: AGPL-3.0

"""屏幕捕获模块。"""

from .capturer import ScreenCapturer
from .region import WindowRegion
from .window import (
    get_dpi_scale,
    get_foreground_window_info,
    get_window_client_region,
    is_window_visible,
)

__all__ = [
    "ScreenCapturer",
    "WindowRegion",
    "get_dpi_scale",
    "get_foreground_window_info",
    "get_window_client_region",
    "is_window_visible",
]
