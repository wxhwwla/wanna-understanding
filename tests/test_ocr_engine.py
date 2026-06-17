# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""OCREngine 后处理与识别集成测试（Mock EasyOCR）。"""

from __future__ import annotations

from PIL import Image

from wanna_understanding.ocr.engine import OCREngine
from wanna_understanding.ocr.recognizer import OCRRecognizer


class _FakeReader:
    def readtext(self, _array: object) -> list:
        return [([[0, 0], [50, 0], [50, 12], [0, 12]], "const fn = () —> null", 0.9)]


def test_engine_recognize_uses_recognizer_and_post_process() -> None:
    recognizer = OCRRecognizer(reader=_FakeReader(), min_confidence=0.5)
    engine = OCREngine(recognizer=recognizer, min_confidence=0.5)
    text = engine.recognize(Image.new("RGB", (40, 20), color="white"))
    assert "->" in text


def test_post_process_deduplicates_adjacent_lines() -> None:
    engine = OCREngine(recognizer=OCRRecognizer(reader=_FakeReader()))
    text = "def foo():\n    return 1\n    return 1\n"
    assert engine._post_process(text) == "def foo():\n    return 1"
