# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""编辑器 OCR 配置：针对 VS Code / Cursor / PyCharm / Trae 等优化预处理参数。"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image

from .theme import detect_dark_theme


@dataclass(frozen=True, slots=True)
class EditorOCRProfile:
    """单种编辑器/主题的 OCR 预处理参数。"""

    name: str
    upscale_factor: float = 3.0
    crop_ratio: float | None = None
    strip_line_numbers: bool = False

    def resolve_crop_ratio(self, default: float) -> float:
        """返回有效裁剪比例。"""
        return self.crop_ratio if self.crop_ratio is not None else default


_PROFILES: dict[str, EditorOCRProfile] = {
    "vscode_dark": EditorOCRProfile(
        name="vscode_dark",
        upscale_factor=3.0,
        crop_ratio=0.72,
        strip_line_numbers=True,
    ),
    "vscode_light": EditorOCRProfile(
        name="vscode_light",
        upscale_factor=3.0,
        crop_ratio=0.72,
        strip_line_numbers=True,
    ),
    "cursor_dark": EditorOCRProfile(
        name="cursor_dark",
        upscale_factor=3.0,
        crop_ratio=0.72,
        strip_line_numbers=True,
    ),
    "trae_dark": EditorOCRProfile(
        name="trae_dark",
        upscale_factor=3.0,
        crop_ratio=0.72,
        strip_line_numbers=True,
    ),
    "pycharm_dark": EditorOCRProfile(
        name="pycharm_dark",
        upscale_factor=3.0,
        crop_ratio=0.68,
        strip_line_numbers=True,
    ),
    "pycharm_light": EditorOCRProfile(
        name="pycharm_light",
        upscale_factor=3.0,
        crop_ratio=0.68,
        strip_line_numbers=True,
    ),
    "generic": EditorOCRProfile(name="generic", upscale_factor=3.0),
}


def get_profile(name: str) -> EditorOCRProfile:
    """按名称获取配置，未知名称回退 generic。"""
    return _PROFILES.get(name, _PROFILES["generic"])


def _is_jetbrains(title: str) -> bool:
    return "pycharm" in title or "intellij" in title


def detect_editor_profile(
    window_title: str,
    image: Image.Image,
    *,
    auto_dark_theme: bool = True,
    forced: str = "auto",
) -> EditorOCRProfile:
    """根据窗口标题与截图推断编辑器 OCR 配置。"""
    if forced != "auto":
        return get_profile(forced)
    title = window_title.casefold()
    dark = detect_dark_theme(image) if auto_dark_theme else False
    if _is_jetbrains(title):
        return _PROFILES["pycharm_dark"] if dark else _PROFILES["pycharm_light"]
    is_vscode = "visual studio code" in title
    is_cursor = "cursor" in title
    is_trae = "trae" in title
    if is_cursor:
        return _PROFILES["cursor_dark"] if dark else _PROFILES["vscode_light"]
    if is_vscode:
        return _PROFILES["vscode_dark"] if dark else _PROFILES["vscode_light"]
    if is_trae:
        return _PROFILES["trae_dark"] if dark else _PROFILES["vscode_light"]
    return _PROFILES["generic"]
