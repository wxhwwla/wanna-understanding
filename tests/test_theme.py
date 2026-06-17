# SPDX-License-Identifier: AGPL-3.0

"""深色主题检测单元测试。"""

from PIL import Image

from wanna_understanding.ocr.theme import detect_dark_theme


def test_detect_dark_theme_on_black_image() -> None:
    image = Image.new("RGB", (40, 20), color=(10, 10, 10))
    assert detect_dark_theme(image) is True


def test_detect_light_theme_on_white_image() -> None:
    image = Image.new("RGB", (40, 20), color=(240, 240, 240))
    assert detect_dark_theme(image) is False
