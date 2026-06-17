# SPDX-License-Identifier: AGPL-3.0

"""悬浮窗定位计算测试。"""

from wanna_understanding.ui.position import compute_overlay_position


def test_flips_to_left_when_no_room_on_right() -> None:
    x, _y = compute_overlay_position(
        window_rect=(100, 50, 1900, 400),
        overlay_width=400,
        overlay_height=100,
        screen_width=1920,
        screen_height=1080,
    )
    assert x < 100


def test_places_on_right_when_room_available() -> None:
    x, y = compute_overlay_position(
        window_rect=(100, 50, 500, 400),
        overlay_width=200,
        overlay_height=100,
        screen_width=1920,
        screen_height=1080,
    )
    assert x == 510
    assert y == 50
