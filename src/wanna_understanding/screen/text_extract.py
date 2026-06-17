# SPDX-License-Identifier: AGPL-3.0

"""文本提取抽象：UI Automation 优先，OCR 兜底。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from PIL import Image

if TYPE_CHECKING:
    from wanna_understanding.ocr.engine import OCREngine
    from wanna_understanding.ocr.profiles import EditorOCRProfile


class TextExtractor(Protocol):
    """从屏幕或窗口提取代码文本。"""

    def extract_text(
        self,
        hwnd: int,
        image: Image.Image | None = None,
        *,
        profile: EditorOCRProfile | None = None,
        is_dark_theme: bool = False,
    ) -> str | None:
        """提取文本；失败返回 None。"""


class UIAutomationTextExtractor:
    """通过 Windows UI Automation 读取编辑器文本（可选依赖）。"""

    def extract_text(
        self,
        hwnd: int,
        image: Image.Image | None = None,
        *,
        profile: EditorOCRProfile | None = None,
        is_dark_theme: bool = False,
    ) -> str | None:
        """尝试从目标窗口控件树读取文本。"""
        del image, profile, is_dark_theme
        try:
            import uiautomation as auto
        except ImportError:
            return None
        if not hwnd:
            return None
        try:
            window = auto.ControlFromHandle(hwnd)
            if window is None or not window.Exists(0, 0):
                return None
            text = self._read_document(window)
            if text and text.strip():
                return text.strip()
            text = self._read_edit(window)
            if text and text.strip():
                return text.strip()
        except Exception:
            return None
        return None

    @staticmethod
    def _read_document(window: object) -> str | None:
        doc = window.DocumentControl(searchDepth=15)  # type: ignore[attr-defined]
        if doc.Exists(0, 0):
            pattern = doc.GetTextPattern()
            if pattern:
                return str(pattern.DocumentRange.GetText(-1))
        return None

    @staticmethod
    def _read_edit(window: object) -> str | None:
        edit = window.EditControl(searchDepth=15)  # type: ignore[attr-defined]
        if edit.Exists(0, 0):
            value = edit.GetValuePattern()
            if value:
                return str(value.Value)
        return None


class OCRTextExtractor:
    """通过 OCR 从截图提取文本。"""

    def __init__(self, engine: OCREngine) -> None:
        self._engine = engine

    def extract_text(
        self,
        hwnd: int,
        image: Image.Image | None = None,
        *,
        profile: EditorOCRProfile | None = None,
        is_dark_theme: bool = False,
    ) -> str | None:
        del hwnd
        if image is None:
            return None
        text = self._engine.recognize(
            image,
            is_dark_theme=is_dark_theme,
            profile=profile,
        )
        stripped = text.strip()
        return stripped if stripped else None


def extract_code_text(
    *,
    hwnd: int,
    image: Image.Image,
    use_uia: bool,
    ocr: OCRTextExtractor,
    uia: UIAutomationTextExtractor | None = None,
    profile: EditorOCRProfile | None = None,
    is_dark_theme: bool = False,
) -> str:
    """按策略链提取代码：UIA（可选）→ OCR。"""
    if use_uia and uia is not None:
        uia_text = uia.extract_text(
            hwnd,
            image,
            profile=profile,
            is_dark_theme=is_dark_theme,
        )
        if uia_text:
            return uia_text
    return ocr.extract_text(
        hwnd,
        image,
        profile=profile,
        is_dark_theme=is_dark_theme,
    ) or ""
