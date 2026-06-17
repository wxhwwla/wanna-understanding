# SPDX-License-Identifier: AGPL-3.0

"""文本提取链测试。"""

from unittest.mock import MagicMock

from PIL import Image

from wanna_understanding.screen.text_extract import (
    OCRTextExtractor,
    UIAutomationTextExtractor,
    extract_code_text,
)


def test_extract_code_text_prefers_uia_when_enabled() -> None:
    image = Image.new("RGB", (10, 10))
    ocr = MagicMock()
    ocr.extract_text.return_value = "ocr text"
    uia = MagicMock()
    uia.extract_text.return_value = "uia text"
    text = extract_code_text(
        hwnd=1,
        image=image,
        use_uia=True,
        ocr=ocr,
        uia=uia,
    )
    assert text == "uia text"
    ocr.extract_text.assert_not_called()


def test_extract_code_text_falls_back_to_ocr() -> None:
    image = Image.new("RGB", (10, 10))
    ocr = MagicMock()
    ocr.extract_text.return_value = "ocr text"
    uia = MagicMock()
    uia.extract_text.return_value = None
    text = extract_code_text(
        hwnd=1,
        image=image,
        use_uia=True,
        ocr=ocr,
        uia=uia,
    )
    assert text == "ocr text"


def test_uia_extractor_returns_none_without_hwnd() -> None:
    extractor = UIAutomationTextExtractor()
    assert extractor.extract_text(0) is None


def test_ocr_extractor_delegates_to_engine() -> None:
    engine = MagicMock()
    engine.recognize.return_value = "  hello  "
    extractor = OCRTextExtractor(engine)
    image = Image.new("RGB", (10, 10))
    assert extractor.extract_text(0, image) == "hello"
    engine.recognize.assert_called_once()
