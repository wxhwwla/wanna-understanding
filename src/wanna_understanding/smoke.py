# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""无 GUI 冒烟测试模块：截图 → OCR →（可选）AI，结果打印到终端。"""

from __future__ import annotations

import sys

from wanna_understanding.ai.client import AIClient
from wanna_understanding.ai.context import trim_to_context
from wanna_understanding.config import Settings, load_settings
from wanna_understanding.logger import add_console_handler, get_logger, setup_logging
from wanna_understanding.ocr.engine import OCREngine
from wanna_understanding.ocr.profiles import detect_editor_profile
from wanna_understanding.ocr.theme import detect_dark_theme
from wanna_understanding.screen.capture_plan import build_monitor_region
from wanna_understanding.screen.capturer import ScreenCapturer
from wanna_understanding.screen.text_extract import (
    OCRTextExtractor,
    UIAutomationTextExtractor,
    extract_code_text,
)
from wanna_understanding.screen.window import (
    get_foreground_window_info,
    is_window_visible,
)

log = get_logger(__name__)


def run_smoke_test(settings: Settings | None = None) -> int:
    """无 GUI 冒烟：截图 → OCR →（可选）AI，结果打印到终端。

    Args:
        settings: 配置，默认从环境加载

    Returns:
        退出码（0 成功，1 失败）
    """
    setup_logging()
    add_console_handler()
    log.info("=== 冒烟测试 ===")

    if sys.platform != "win32":
        print("错误：冒烟测试仅支持 Windows。")
        return 1
    cfg = settings or load_settings()
    capturer = ScreenCapturer()
    ocr = OCREngine()
    hwnd, title = get_foreground_window_info()
    print(f"活动窗口: {title!r} (hwnd={hwnd})")
    if not is_window_visible(hwnd):
        print("窗口不可见或已最小化。")
        return 1
    region = build_monitor_region(
        hwnd,
        title,
        monitor_mode=cfg.monitor_mode,
        monitor_rect=cfg.monitor_rect,
        crop_ratio=cfg.crop_ratio,
        editor_profile=cfg.editor_profile,
    )
    image = capturer.capture(region)
    ocr_extractor = OCRTextExtractor(ocr)
    uia_extractor = UIAutomationTextExtractor()
    profile = detect_editor_profile(
        title,
        image,
        auto_dark_theme=cfg.auto_dark_theme,
        forced=cfg.editor_profile,
    )
    is_dark = (
        profile.name.endswith("_dark")
        or (
            profile.name == "generic"
            and (detect_dark_theme(image) if cfg.auto_dark_theme else cfg.dark_theme)
        )
    )
    print(f"编辑器配置: {profile.name}（{'深色' if is_dark else '浅色'}）")
    if cfg.use_uia:
        print("文本提取: UIA 优先")
    code = extract_code_text(
        hwnd=hwnd,
        image=image,
        use_uia=cfg.use_uia,
        ocr=ocr_extractor,
        uia=uia_extractor,
        window_title=title,
        profile=profile,
        is_dark_theme=is_dark,
    )
    print("--- OCR 结果 ---")
    print(code or "(空)")
    trimmed = trim_to_context(code, cfg.context_max_lines)
    if trimmed != code:
        print(f"--- 裁剪后 ({cfg.context_max_lines} 行) ---")
        print(trimmed)
    if not cfg.has_api_key:
        print("\n未配置 DEEPSEEK_API_KEY，跳过 AI 分析。")
        return 0
    client = AIClient(cfg)
    try:
        result = client.analyze(trimmed)
        print("\n--- AI 分析 ---")
        print(result.format_display())
    finally:
        client.close()
    return 0
