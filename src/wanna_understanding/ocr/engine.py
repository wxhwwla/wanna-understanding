# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""OCR 引擎：预处理 + EasyOCR 识别 + 代码文本后处理。"""

from __future__ import annotations

import re

from PIL import Image

from wanna_understanding.logger import get_logger

from .preprocess import ImagePreprocessor
from .profiles import EditorOCRProfile
from .recognizer import OCRRecognizer

log = get_logger(__name__)

_SYMBOL_FIXES: tuple[tuple[str, str], ...] = (
    (r"\bl\b", "1"),
    (r"\bO\b", "0"),
    (r"—>", "->"),
    (r"==>", "=>"),  # EasyOCR 有时把 => 识别为 ==>
    (r"\*\*", "**"),
    (r"\|", "|"),   # 确保竖线保留
    (r"—", "——"),   # 长破折号保持
    (r"\bnull\b", "None"),
)


class OCREngine:
    """从截图提取代码文本。"""

    def __init__(
        self,
        preprocessor: ImagePreprocessor | None = None,
        recognizer: OCRRecognizer | None = None,
        min_confidence: float = 0.2,
        lang_list: list[str] | None = None,
    ) -> None:
        self._preprocessor = preprocessor or ImagePreprocessor()
        self._recognizer = recognizer
        self._min_confidence = min_confidence
        # 默认中英混合（ch_sim + en）；首次加载会下载 ~50MB 模型
        self._lang_list = lang_list or ["en", "ch_sim"]

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
        profile_name = profile.name if profile else "none"
        log.debug(
            "OCR 开始: profile=%s, dark=%s, img=%dx%d",
            profile_name, is_dark_theme, image.width, image.height,
        )
        processed = self._preprocessor.process(
            image,
            is_dark_theme=is_dark_theme,
            profile=profile,
        )
        result = self._ensure_recognizer().recognize_image(processed)
        log.debug(
            "OCR 原始结果: %d 项, 耗时 %.0fms",
            len(result.texts), result.inference_ms,
        )
        # 记录每个识别项的置信度（前 20 项，方便诊断）
        for i, item in enumerate(result.texts[:20]):
            log.debug("  OCR[%d] conf=%.2f: %r", i, item.confidence, item.text[:60])
        lines = [
            item.text
            for item in result.texts
            if item.confidence >= self._min_confidence and item.text.strip()
        ]
        combined = self._post_process("\n".join(lines))
        log.debug(
            "OCR 最终: %d 字符 (过滤后 %d 行)",
            len(combined), len(combined.splitlines()) if combined else 0,
        )
        if combined:
            log.debug("OCR 内容前 100 字符: %r", combined[:100])
        return combined

    def _post_process(self, text: str) -> str:
        """修复常见 OCR 误识别并去除相邻重复行。"""
        if not text.strip():
            return ""
        fixed = text
        for pattern, replacement in _SYMBOL_FIXES:
            fixed = re.sub(pattern, replacement, fixed)
        # 过滤行号：单独的数字行（编辑器行号），如 " 4", " 5  ", "6"
        cleaned: list[str] = []
        for line in fixed.splitlines():
            stripped = line.strip()
            # 跳过纯数字行（编辑器行号）
            if re.fullmatch(r"\d+", stripped):
                continue
            # 跳过只有一个字母的行（可能是行号误识别）
            if re.fullmatch(r"[a-zA-Z]", stripped):
                continue
            cleaned.append(line.rstrip())
        # 去重
        deduped: list[str] = []
        for line in cleaned:
            if deduped and deduped[-1] == line:
                continue
            deduped.append(line)
        return "\n".join(deduped).strip()
