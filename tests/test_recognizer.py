# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""OCRRecognizer 单元测试（Mock EasyOCR，无需安装模型）。"""

from __future__ import annotations

from PIL import Image

from wanna_understanding.ocr.recognizer import OCRRecognizer


class _FakeReader:
    def readtext(self, _array: object) -> list:
        return [
            ([[0, 0], [80, 0], [80, 16], [0, 16]], "def foo():", 0.92),
            ([[0, 20], [90, 20], [90, 36], [0, 36]], "    return 1", 0.88),
        ]


def test_recognize_image_sorts_lines_top_to_bottom() -> None:
    recognizer = OCRRecognizer(reader=_FakeReader(), min_confidence=0.5)
    result = recognizer.recognize_image(Image.new("RGB", (120, 60), color="white"))
    assert result.raw_texts == ["def foo():", "    return 1"]


def test_recognize_image_filters_low_confidence() -> None:
    class LowConfReader:
        def readtext(self, _array: object) -> list:
            return [([[0, 0], [10, 0], [10, 10], [0, 10]], "noise", 0.1)]

    recognizer = OCRRecognizer(reader=LowConfReader(), min_confidence=0.5)
    result = recognizer.recognize_image(Image.new("RGB", (20, 20), color="white"))
    assert result.raw_texts == []
