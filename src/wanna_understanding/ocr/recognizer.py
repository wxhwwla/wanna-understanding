# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""EasyOCR 文本识别器 — 改编自 endfield_damage_calculator/tools/ocr/recognizer.py。"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

try:
    import easyocr
except ImportError:
    easyocr = None  # type: ignore[assignment, misc]


@dataclass
class OCRText:
    """单个 OCR 识别结果。"""

    text: str
    confidence: float
    corrected: bool = False

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""
        return {
            "text": self.text,
            "confidence": round(self.confidence, 4),
            "corrected": self.corrected,
        }


@dataclass
class OCRResult:
    """单张图片的 OCR 结果。"""

    image_path: str
    texts: list[OCRText] = field(default_factory=list)
    inference_ms: float = 0.0

    @property
    def raw_texts(self) -> list[str]:
        """按阅读顺序排列的文本行。"""
        return [item.text for item in self.texts]

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。"""
        return {
            "image_path": self.image_path,
            "num_texts": len(self.texts),
            "inference_ms": round(self.inference_ms, 1),
            "texts": [item.to_dict() for item in self.texts],
        }


class OCRRecognizer:
    """EasyOCR 封装，支持文件路径与 PIL 图像输入。"""

    def __init__(
        self,
        lang_list: list[str] | None = None,
        gpu: bool = False,
        min_confidence: float = 0.3,
        term_dict: dict[str, str] | None = None,
        reader: Any | None = None,
    ) -> None:
        if reader is None and easyocr is None:
            msg = '需要安装 EasyOCR：pip install -e ".[ocr]"'
            raise ImportError(msg)
        self._lang = lang_list or ["en"]
        self._gpu = gpu
        self._min_confidence = min_confidence
        self._term_dict = term_dict or {}
        self._reader = reader
        self._reader_lock = threading.Lock()

    def warmup(self) -> None:
        """预加载 EasyOCR 模型（首次调用可能较慢）。"""
        self._ensure_reader()

    def _ensure_reader(self) -> Any:
        if self._reader is not None:
            return self._reader
        with self._reader_lock:
            if self._reader is None:
                self._reader = easyocr.Reader(self._lang, gpu=self._gpu)
        return self._reader

    def recognize(self, image_path: str | Path) -> OCRResult:
        """识别整张图片的文本。"""
        path = Path(image_path)
        if not path.is_file():
            msg = f"图片不存在: {image_path}"
            raise FileNotFoundError(msg)
        image = Image.open(path)
        return self.recognize_image(image, source=str(path))

    def recognize_image(
        self,
        image: Image.Image,
        *,
        source: str = "<memory>",
    ) -> OCRResult:
        """识别 PIL 图像中的文本。"""
        import numpy as np

        array = np.asarray(image.convert("RGB"))
        started = time.perf_counter()
        # 调低 text_threshold/low_text 提高对小字和特殊符号的敏感度
        raw = self._ensure_reader().readtext(
            array,
            text_threshold=0.5,
            low_text=0.3,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        return OCRResult(
            image_path=source,
            texts=self._parse_raw(raw),
            inference_ms=elapsed_ms,
        )

    def _parse_raw(self, raw: list[Any]) -> list[OCRText]:
        """按从上到下、从左到右排序后解析 EasyOCR 输出。

        paragraph=True 时 EasyOCR 的输出格式会变化：
        - 普通模式：list of (bbox, text, confidence)
        - 段落模式：list of (text, confidence) — bbox 被合并丢弃
        此方法兼容两种格式。
        """
        ranked: list[tuple[float, float, str, float]] = []
        for item in raw:
            # 兼容 (text, confidence) 和 (bbox, text, confidence) 两种格式
            if len(item) == 2:
                text, confidence = item
                y_center = 0.0
                x_left = 0.0
            else:
                bbox, text, confidence = item[:3]
                y_center = (bbox[0][1] + bbox[2][1]) / 2
                x_left = bbox[0][0]
            # paragraph=True 时 confidence 可能为 None，直接保留
            if confidence is not None:
                score = float(confidence)
                if score < self._min_confidence:
                    continue
            else:
                score = 1.0  # 段落模式无置信度，视为高置信
            cleaned = str(text).rstrip("\n\r")
            if not cleaned.strip():
                continue
            ranked.append((y_center, x_left, cleaned, score))
        ranked.sort(key=lambda item: (item[0], item[1]))

        texts: list[OCRText] = []
        for _y, _x, text, score in ranked:
            corrected = self._apply_term_dict(text)
            texts.append(
                OCRText(
                    text=corrected,
                    confidence=score,
                    corrected=corrected != text,
                )
            )
        return texts

    def _apply_term_dict(self, text: str) -> str:
        if text in self._term_dict:
            return self._term_dict[text]
        return text
