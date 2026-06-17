# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""自定义监控区域解析测试。"""

from wanna_understanding.screen.custom_region import (
    ScreenRect,
    format_monitor_rect,
    parse_monitor_rect,
)


def test_parse_monitor_rect_valid() -> None:
    rect = parse_monitor_rect("100,200,800,600")
    assert rect == ScreenRect(x=100, y=200, width=800, height=600)


def test_parse_monitor_rect_rejects_invalid() -> None:
    assert parse_monitor_rect("") is None
    assert parse_monitor_rect("1,2,3") is None
    assert parse_monitor_rect("a,b,c,d") is None
    assert parse_monitor_rect("0,0,0,10") is None


def test_format_roundtrip() -> None:
    rect = ScreenRect(x=10, y=20, width=300, height=400)
    assert parse_monitor_rect(format_monitor_rect(rect)) == rect


def test_to_region_uses_screen_coords() -> None:
    region = ScreenRect(x=5, y=6, width=100, height=50).to_region()
    assert region.x == 5
    assert region.y == 6
    assert region.dpi_scale == 1.0
