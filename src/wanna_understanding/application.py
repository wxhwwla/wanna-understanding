# SPDX-License-Identifier: AGPL-3.0

"""应用编排：串联截图、OCR、触发、AI 与悬浮窗。"""

from __future__ import annotations

import hashlib
import sys
import threading
import traceback

from PIL import Image

from wanna_understanding.ai.cache import AnalysisResult, ResultCache
from wanna_understanding.ai.client import AIClient
from wanna_understanding.ai.context import trim_to_context
from wanna_understanding.config import Settings, load_settings
from wanna_understanding.ocr.engine import OCREngine
from wanna_understanding.ocr.profiles import detect_editor_profile
from wanna_understanding.ocr.theme import detect_dark_theme
from wanna_understanding.screen.capture_plan import build_monitor_region
from wanna_understanding.screen.capturer import ScreenCapturer
from wanna_understanding.screen.region import WindowRegion
from wanna_understanding.screen.text_extract import (
    OCRTextExtractor,
    UIAutomationTextExtractor,
    extract_code_text,
)
from wanna_understanding.screen.window import (
    get_foreground_window_info,
    is_window_visible,
)
from wanna_understanding.trigger.watcher import ContentWatcher
from wanna_understanding.ui.hotkey import hotkey_toggle_pressed
from wanna_understanding.ui.overlay import OverlayWindow
from wanna_understanding.ui.streaming import StreamUpdateThrottler


class Application:
    """主应用：轮询截图哈希，稳定后 OCR + AI 分析。"""

    def __init__(self, settings: Settings | None = None) -> None:
        if sys.platform != "win32":
            msg = "Wanna Understanding 当前仅支持 Windows"
            raise OSError(msg)
        self.settings = settings or load_settings()
        self.capturer = ScreenCapturer()
        self.ocr = OCREngine()
        self.ai = AIClient(self.settings)
        self.cache = ResultCache(max_size=self.settings.cache_max_size)
        self.overlay = OverlayWindow(
            width=self.settings.overlay_width,
            height=self.settings.overlay_height,
            opacity=self.settings.overlay_opacity,
        )
        self._latest_image: Image.Image | None = None
        self._latest_title: str = ""
        self._latest_hwnd: int = 0
        self._ocr_extractor = OCRTextExtractor(self.ocr)
        self._uia_extractor = UIAutomationTextExtractor()
        self._analyzing = False
        self._hotkey_was_down = False
        self.watcher = ContentWatcher(
            hash_provider=self._capture_hash,
            debounce_delay=self.settings.debounce_delay,
        )

    def run(self) -> None:
        """启动主循环。"""
        self.overlay.show_status(self._startup_message())
        self.overlay.set_poll_callback(
            int(self.settings.poll_interval * 1000),
            self._on_poll,
        )
        self.overlay.mainloop()
        self.ai.close()

    def _startup_message(self) -> str:
        lines = [
            "Wanna Understanding 已启动",
            "正在监控活动窗口…",
            f"轮询间隔：{self.settings.poll_interval}s",
            f"防抖延迟：{self.settings.debounce_delay}s",
            f"局部发送：最多 {self.settings.context_max_lines} 行",
            "快捷键：Ctrl+Shift+H 显示/隐藏",
        ]
        if self.settings.stream_output:
            lines.append("AI 输出：流式")
        elif not self.settings.stream_output:
            lines.append("AI 输出：完整等待模式")
        if self.settings.auto_dark_theme:
            lines.append("深色主题：自动检测")
        if self.settings.monitor_mode == "custom":
            lines.append(f"监控模式：自定义区域 ({self.settings.monitor_rect or '未配置'})")
        if self.settings.use_uia:
            lines.append("文本提取：UI Automation 优先")
        if not self.settings.has_api_key:
            lines.append("")
            lines.append("提示：未配置 DEEPSEEK_API_KEY，将仅展示 OCR 状态。")
        return "\n".join(lines)

    def _on_poll(self) -> None:
        try:
            self._handle_hotkey()
            hwnd, title = get_foreground_window_info()
            if not is_window_visible(hwnd):
                self.overlay.hide()
                return
            if self.watcher.on_window_changed(hwnd):
                self.cache.clear()
                self.overlay.show_status(f"已切换窗口：{title}\n等待内容稳定…")
            region = self._build_capture_region(hwnd, title)
            rect = (
                region.x,
                region.y,
                region.x + region.width,
                region.y + region.height,
            )
            if self.overlay.is_visible:
                self.overlay.show_near(rect)
            settled_hash = self.watcher.poll()
            if settled_hash and not self._analyzing:
                self._start_analysis()
        except Exception as exc:
            self.overlay.show_status(f"监控异常：{exc}")

    def _handle_hotkey(self) -> None:
        if not self.settings.hotkey_toggle:
            return
        pressed = hotkey_toggle_pressed()
        if pressed and not self._hotkey_was_down:
            visible = self.overlay.toggle_visibility()
            if not visible:
                self.overlay.show_status("悬浮窗已隐藏（Ctrl+Shift+H 恢复）")
        self._hotkey_was_down = pressed

    def _build_capture_region(self, hwnd: int, title: str) -> WindowRegion:
        return build_monitor_region(
            hwnd,
            title,
            monitor_mode=self.settings.monitor_mode,
            monitor_rect=self.settings.monitor_rect,
            crop_ratio=self.settings.crop_ratio,
            editor_profile=self.settings.editor_profile,
        )

    def _capture_hash(self) -> str:
        hwnd, title = get_foreground_window_info()
        if not is_window_visible(hwnd):
            return ""
        self._latest_hwnd = hwnd
        self._latest_title = title
        region = self._build_capture_region(hwnd, title)
        image = self.capturer.capture(region)
        self._latest_image = image
        return ScreenCapturer.hash_image(image)

    def _resolve_dark_theme(self, image: Image.Image, profile_name: str) -> bool:
        if profile_name.endswith("_dark"):
            return True
        if profile_name.endswith("_light"):
            return False
        if self.settings.auto_dark_theme:
            from wanna_understanding.ocr.theme import detect_dark_theme

            return detect_dark_theme(image)
        return self.settings.dark_theme

    def _start_analysis(self) -> None:
        if self._latest_image is None:
            return
        self._analyzing = True
        image = self._latest_image.copy()
        self.overlay.show_status("正在识别代码…")

        def work() -> None:
            try:
                profile = detect_editor_profile(
                    self._latest_title,
                    image,
                    auto_dark_theme=self.settings.auto_dark_theme,
                    forced=self.settings.editor_profile,
                )
                is_dark = self._resolve_dark_theme(image, profile.name)
                code = extract_code_text(
                    hwnd=self._latest_hwnd,
                    image=image,
                    use_uia=self.settings.use_uia,
                    ocr=self._ocr_extractor,
                    uia=self._uia_extractor,
                    profile=profile,
                    is_dark_theme=is_dark,
                )
                if not code.strip():
                    self._schedule_status(
                        "未识别到有效代码，请确保编辑器中有可见代码。"
                    )
                    return
                trimmed = trim_to_context(code, self.settings.context_max_lines)
                code_hash = hashlib.sha256(trimmed.encode("utf-8")).hexdigest()
                cached = self.cache.get(code_hash)
                if cached:
                    self._schedule_result(cached)
                    return
                result = self._run_ai_analysis(trimmed, code_hash)
                self.cache.put(code_hash, result)
                self._schedule_result(result)
            except Exception as exc:
                detail = traceback.format_exc(limit=2)
                self._schedule_status(f"分析失败：{exc}\n\n{detail}")
            finally:
                self._analyzing = False

        threading.Thread(target=work, daemon=True).start()

    def _run_ai_analysis(self, code: str, code_hash: str) -> AnalysisResult:
        """调用 AI；流式模式下边生成边刷新悬浮窗。"""
        if not self.settings.stream_output:
            self._schedule_status("正在调用 AI 分析…")
            return self.ai.analyze(code, code_hash=code_hash)

        throttler = StreamUpdateThrottler(
            emit=lambda text: self.overlay.schedule(
                lambda t=text: self.overlay.show_streaming(t)
            ),
            min_interval=self.settings.stream_ui_interval,
        )

        def on_delta(_delta: str, accumulated: str) -> None:
            throttler.push(accumulated)

        self.overlay.schedule(lambda: self.overlay.show_streaming(""))
        result = self.ai.analyze_stream(
            code,
            on_delta=on_delta,
            code_hash=code_hash,
        )
        throttler.flush()
        return result

    def _schedule_status(self, message: str) -> None:
        self.overlay.schedule(lambda: self.overlay.show_status(message))

    def _schedule_result(self, result: AnalysisResult) -> None:
        self.overlay.schedule(lambda: self.overlay.update_content(result))


def run_smoke_test(settings: Settings | None = None) -> int:
    """无 GUI 冒烟：截图 → OCR →（可选）AI，结果打印到终端。"""
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
