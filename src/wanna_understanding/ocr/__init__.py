# SPDX-License-Identifier: AGPL-3.0

"""OCR 文字识别模块。"""

from .engine import OCREngine
from .preprocess import ImagePreprocessor
from .profiles import EditorOCRProfile, detect_editor_profile, get_profile
from .recognizer import OCRRecognizer, OCRResult, OCRText
from .theme import detect_dark_theme

__all__ = [
    "EditorOCRProfile",
    "ImagePreprocessor",
    "OCREngine",
    "OCRRecognizer",
    "OCRResult",
    "OCRText",
    "detect_dark_theme",
    "detect_editor_profile",
    "get_profile",
]
