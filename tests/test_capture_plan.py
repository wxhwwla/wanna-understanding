# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""截图区域规划测试。"""

from unittest.mock import patch

from wanna_understanding.screen.capture_plan import (
    build_monitor_region,
    crop_ratio_for_title,
    should_strip_line_numbers,
)
from wanna_understanding.screen.region import WindowRegion


def test_crop_ratio_pycharm() -> None:
    assert crop_ratio_for_title("app.py - PyCharm", default_ratio=0.7) == 0.68


def test_strip_line_numbers_pycharm() -> None:
    assert should_strip_line_numbers("main.py - IntelliJ IDEA") is True
    assert should_strip_line_numbers("记事本") is False


@patch("wanna_understanding.screen.capture_plan.get_window_client_region")
def test_build_monitor_region_custom(mock_region) -> None:
    mock_region.return_value = WindowRegion(hwnd=1, x=0, y=0, width=100, height=100)
    region = build_monitor_region(
        1,
        "x",
        monitor_mode="custom",
        monitor_rect="50,60,200,150",
        crop_ratio=0.7,
    )
    assert region.x == 50
    assert region.width == 200
    mock_region.assert_not_called()


@patch("wanna_understanding.screen.capture_plan.get_window_client_region")
def test_build_monitor_region_strips_pycharm_line_numbers(mock_region) -> None:
    mock_region.return_value = WindowRegion(hwnd=1, x=0, y=0, width=200, height=100)
    region = build_monitor_region(
        1,
        "main.py - PyCharm",
        monitor_mode="window",
        monitor_rect="",
        crop_ratio=0.7,
    )
    assert region.x > 0
    assert region.width < 200 * 0.68
