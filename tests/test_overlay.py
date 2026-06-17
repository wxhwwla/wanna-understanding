# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""悬浮窗定位计算测试。"""

from wanna_understanding.ui.position import compute_overlay_position


def test_flips_to_left_when_no_room_on_right() -> None:
    work_area = (0, 0, 1920, 1080)
    x, _y = compute_overlay_position(
        window_rect=(100, 50, 1900, 400),
        overlay_width=400,
        overlay_height=100,
        work_area=work_area,
    )
    assert x < 100


def test_places_on_right_when_room_available() -> None:
    work_area = (0, 0, 1920, 1080)
    x, y = compute_overlay_position(
        window_rect=(100, 50, 500, 400),
        overlay_width=200,
        overlay_height=100,
        work_area=work_area,
    )
    assert x == 510
    assert y == 50


def test_respects_monitor_work_area_offset() -> None:
    work_area = (1920, 0, 3840, 1080)
    x, y = compute_overlay_position(
        window_rect=(2000, 100, 2600, 500),
        overlay_width=200,
        overlay_height=100,
        work_area=work_area,
    )
    assert x == 2610
    assert y == 100
