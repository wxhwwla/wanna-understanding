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
from wanna_understanding.config import Settings, load_settings
from wanna_understanding.ocr.engine import OCREngine
from wanna_understanding.screen.capturer import ScreenCapturer
from wanna_understanding.screen.window import (
    get_foreground_window_info,
    get_window_client_region,
    is_window_visible,
)
from wanna_understanding.trigger.watcher import ContentWatcher
from wanna_understanding.ui.overlay import OverlayWindow


class Application:
    """MVP 主应用：轮询截图哈希，稳定后 OCR + AI 分析。"""

    def __init__(self, settings: Settings | None = None) -> None:
        if sys.platform != "win32":
            msg = "Wanna Understanding MVP 当前仅支持 Windows"
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
        self._analyzing = False
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
        ]
        if not self.settings.has_api_key:
            lines.append("")
            lines.append("提示：未配置 DEEPSEEK_API_KEY，将仅展示 OCR 状态。")
        return "\n".join(lines)

    def _on_poll(self) -> None:
        try:
            hwnd, title = get_foreground_window_info()
            if not is_window_visible(hwnd):
                self.overlay.hide()
                return
            if self.watcher.on_window_changed(hwnd):
                self.cache.clear()
                self.overlay.show_status(f"已切换窗口：{title}\n等待内容稳定…")
            region = get_window_client_region(hwnd)
            rect = (
                region.x,
                region.y,
                region.x + region.width,
                region.y + region.height,
            )
            self.overlay.show_near(rect)
            settled_hash = self.watcher.poll()
            if settled_hash and not self._analyzing:
                self._start_analysis()
        except Exception as exc:
            self.overlay.show_status(f"监控异常：{exc}")

    def _capture_hash(self) -> str:
        hwnd, _title = get_foreground_window_info()
        if not is_window_visible(hwnd):
            return ""
        region = get_window_client_region(hwnd).center_crop(self.settings.crop_ratio)
        image = self.capturer.capture(region)
        self._latest_image = image
        return ScreenCapturer.hash_image(image)

    def _start_analysis(self) -> None:
        if self._latest_image is None:
            return
        self._analyzing = True
        image = self._latest_image.copy()
        self.overlay.show_status("正在识别代码…")

        def work() -> None:
            try:
                code = self.ocr.recognize(image, is_dark_theme=self.settings.dark_theme)
                if not code.strip():
                    self._schedule_status(
                        "未识别到有效代码，请确保编辑器中有可见代码。"
                    )
                    return
                code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
                cached = self.cache.get(code_hash)
                if cached:
                    self._schedule_result(cached)
                    return
                self._schedule_status("正在调用 AI 分析…")
                result = self.ai.analyze(code, code_hash=code_hash)
                self.cache.put(code_hash, result)
                self._schedule_result(result)
            except Exception as exc:
                detail = traceback.format_exc(limit=2)
                self._schedule_status(f"分析失败：{exc}\n\n{detail}")
            finally:
                self._analyzing = False

        threading.Thread(target=work, daemon=True).start()

    def _schedule_status(self, message: str) -> None:
        self.overlay.schedule(lambda: self.overlay.show_status(message))

    def _schedule_result(self, result: AnalysisResult) -> None:
        self.overlay.schedule(lambda: self.overlay.update_content(result))
