# SPDX-License-Identifier: AGPL-3.0

"""OCR 引擎：预处理 + EasyOCR 识别 + 代码文本后处理。"""

from __future__ import annotations

import re

from PIL import Image

from .preprocess import ImagePreprocessor
from .profiles import EditorOCRProfile
from .recognizer import OCRRecognizer

_SYMBOL_FIXES: tuple[tuple[str, str], ...] = (
    (r"\bl\b", "1"),
    (r"\bO\b", "0"),
    (r"—>", "->"),
    (r"=>", "=>"),
    (r"\*\*", "**"),
)


class OCREngine:
    """从截图提取代码文本。"""

    def __init__(
        self,
        preprocessor: ImagePreprocessor | None = None,
        recognizer: OCRRecognizer | None = None,
        min_confidence: float = 0.5,
        lang_list: list[str] | None = None,
    ) -> None:
        self._preprocessor = preprocessor or ImagePreprocessor()
        self._recognizer = recognizer
        self._min_confidence = min_confidence
        self._lang_list = lang_list

    def _ensure_recognizer(self) -> OCRRecognizer:
        if self._recognizer is None:
            self._recognizer = OCRRecognizer(
                lang_list=self._lang_list,
                min_confidence=self._min_confidence,
            )
        return self._recognizer

    def warmup(self) -> None:
        """预加载 OCR 模型，避免首次分析长时间无响应。"""
        self._ensure_recognizer().warmup()

    def recognize(
        self,
        image: Image.Image,
        is_dark_theme: bool = False,
        profile: EditorOCRProfile | None = None,
    ) -> str:
        """识别图像中的文本并返回后处理后的代码字符串。"""
        processed = self._preprocessor.process(
            image,
            is_dark_theme=is_dark_theme,
            profile=profile,
        )
        result = self._ensure_recognizer().recognize_image(processed)
        lines = [
            item.text
            for item in result.texts
            if item.confidence >= self._min_confidence and item.text.strip()
        ]
        return self._post_process("\n".join(lines))

    def _post_process(self, text: str) -> str:
        """修复常见 OCR 误识别并去除相邻重复行。"""
        if not text.strip():
            return ""
        fixed = text
        for pattern, replacement in _SYMBOL_FIXES:
            fixed = re.sub(pattern, replacement, fixed)
        deduped: list[str] = []
        for line in fixed.splitlines():
            stripped = line.rstrip()
            if deduped and deduped[-1] == stripped:
                continue
            deduped.append(stripped)
        return "\n".join(deduped).strip()
