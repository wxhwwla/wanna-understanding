# SPDX-License-Identifier: AGPL-3.0

"""WindowRegion 单元测试。"""

from wanna_understanding.screen.region import WindowRegion


def test_physical_rect_applies_dpi_scale() -> None:
    region = WindowRegion(hwnd=1, x=10, y=20, width=100, height=50, dpi_scale=2.0)
    assert region.physical_rect() == (10, 20, 200, 100)


def test_center_crop_reduces_area() -> None:
    region = WindowRegion(hwnd=1, x=0, y=0, width=100, height=100, dpi_scale=1.0)
    cropped = region.center_crop(0.7)
    assert cropped.width == 70
    assert cropped.height == 70
    assert cropped.x == 15
    assert cropped.y == 15


def test_strip_line_numbers_trims_left() -> None:
    region = WindowRegion(hwnd=1, x=0, y=0, width=200, height=100, dpi_scale=1.0)
    stripped = region.strip_line_numbers(0.1)
    assert stripped.x == 20
    assert stripped.width == 180
