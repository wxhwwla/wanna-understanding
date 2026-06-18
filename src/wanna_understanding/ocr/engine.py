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
    # ── 以下针对 Python 代码常见 OCR 误识 ──
    (r"(?<![a-zA-Z])iport(?![a-zA-Z])", "import"),  # import → iport
    (r"(?<=from\s)_(?=\s)", "__"),                   # from _ → from __
    (r"_(\s)", r"__\1"),                             # 单下划线+空格 → 双下划线+空格（修复 `_ ` → `__ `）
    (r"\bSy5\b", "sys"),                             # sys → Sy5
    (r"PathC", "Path("),                             # Path( → PathC
    (r"([a-z])C([a-z])", r"\1(\2"),                  # 字母C字母 → 字母(字母 (修复 C 被误读为 ()
    (r"file-\)", "file)"),                           # file) → file-) 修复
    (r"\_file\_", "__file__"),                       # _file_ → __file__
    (r"\bFi1e\b", "File"),                           # File → Fi1e
    (r"\bC1ass\b", "Class"),                         # Class → C1ass
    (r"\bDe1\b", "Del"),                             # del → de1 (小写 l 与 1 混淆)
    (r"\bSe1f\b", "Self"),                           # self → Se1f
    (r"\bde1\b", "del"),
    (r"\bse1f\b", "self"),
    (r"\bTrue\b", "True"),                           # True → Ture 等变体
    (r"\bTure\b", "True"),
    (r"\bFa1se\b", "False"),
    (r"\bNone\b", "None"),
    (r"\bnu11\b", "null"),                           # 小写 L 替代数字 1
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
        # 默认纯英文；ch_sim 会严重干扰 Python 特殊符号（_() 等）的识别。
        # 如需中英文混合代码，在设置中手动添加 ch_sim 或通过 WU_OCR_LANG 环境变量设定。
        self._lang_list = lang_list or ["en"]

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
        # 过滤行号：编辑器行号或噪声，如 "4", " 5  ", "6.", "7,"
        _NOISE_PATTERNS = (
            re.compile(r"^\d{1,3}$"),              # "2", " 5 ", "123"
            re.compile(r"^\d{1,3}[.,;:\-]$"),       # "2.", "3,", "4:"
            re.compile(r"^[a-zA-Z]$"),              # "F", "x" (行号误识别)
        )
        cleaned: list[str] = []
        for line in fixed.splitlines():
            stripped = line.strip()
            if any(p.match(stripped) for p in _NOISE_PATTERNS):
                continue
            cleaned.append(line.rstrip())
        # 去重
        deduped: list[str] = []
        for line in cleaned:
            if deduped and deduped[-1] == line:
                continue
            deduped.append(line)
        return "\n".join(deduped).strip()
