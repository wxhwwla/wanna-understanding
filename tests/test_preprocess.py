# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""ImagePreprocessor 单元测试。"""

from PIL import Image

from wanna_understanding.ocr.preprocess import ImagePreprocessor


def test_process_returns_grayscale_image() -> None:
    image = Image.new("RGB", (20, 10), color=(30, 30, 30))
    processed = ImagePreprocessor().process(image, is_dark_theme=True)
    assert processed.mode == "L"
    assert processed.size == (60, 30)


def test_process_sharpens_and_enhances_contrast() -> None:
    image = Image.new("RGB", (20, 10), color=(200, 200, 200))
    processed = ImagePreprocessor().process(image, is_dark_theme=False)
    assert processed.mode == "L"
    assert processed.size == (60, 30)
