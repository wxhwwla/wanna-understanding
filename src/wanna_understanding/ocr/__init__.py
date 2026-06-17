# SPDX-License-Identifier: AGPL-3.0

"""OCR 文字识别模块。"""

from .engine import OCREngine
from .preprocess import ImagePreprocessor
from .recognizer import OCRRecognizer, OCRResult, OCRText
from .theme import detect_dark_theme

__all__ = [
    "ImagePreprocessor",
    "OCREngine",
    "OCRRecognizer",
    "OCRResult",
    "OCRText",
    "detect_dark_theme",
]
