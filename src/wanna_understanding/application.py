# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""应用编排：串联截图、OCR、触发、AI 与悬浮窗。"""

from __future__ import annotations

import sys
import threading
import time

from PIL import Image

from wanna_understanding.ai.cache import ResultCache
from wanna_understanding.ai.client import AIClient
from wanna_understanding.ai.history import HistoryStore
from wanna_understanding.analysis_coordinator import AnalysisCoordinator
from wanna_understanding.config import Settings, get_data_dir, load_settings
from wanna_understanding.logger import add_console_handler, get_logger, setup_logging
from wanna_understanding.ocr.engine import OCREngine
from wanna_understanding.screen.capture_plan import build_monitor_region
from wanna_understanding.screen.capturer import ScreenCapturer
from wanna_understanding.screen.region import WindowRegion
from wanna_understanding.screen.text_extract import (
    OCRTextExtractor,
    UIAutomationTextExtractor,
)
from wanna_understanding.screen.window import (
    get_foreground_window_info,
    is_window_visible,
)
from wanna_understanding.trigger.watcher import ContentWatcher
from wanna_understanding.ui.history_dialog import HistoryDialog
from wanna_understanding.ui.hotkey import (
    hotkey_freeze_pressed,
    hotkey_history_pressed,
    hotkey_settings_pressed,
    hotkey_toggle_pressed,
)
from wanna_understanding.ui.overlay import OverlayWindow
from wanna_understanding.ui.settings_dialog import SettingsDialog
from wanna_understanding.ui.tray import TrayController

log = get_logger(__name__)


class Application(AnalysisCoordinator):
    """主应用：轮询截图哈希，稳定后 OCR + AI 分析。"""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        tray_enabled: bool | None = None,
    ) -> None:
        if sys.platform != "win32":
            msg = "Wanna Understanding 当前仅支持 Windows"
            raise OSError(msg)
        # 初始化日志系统（首次创建 Application 实例时）
        log_path = setup_logging()
        add_console_handler()
        import wanna_understanding as _pkg

        log.info("=== Wanna Understanding v%s 启动 ===", _pkg.__version__)
        log.info("日志路径: %s", log_path)
        self.settings = settings or load_settings()
        if tray_enabled is not None:
            self.settings = self.settings.model_copy(
                update={"tray_enabled": tray_enabled}
            )
        self.capturer = ScreenCapturer()
        self.ocr = OCREngine()
        self.ai = AIClient(self.settings)
        self.cache = ResultCache(max_size=self.settings.cache_max_size)
        self.history = HistoryStore(
            path=get_data_dir() / "history.json",
            max_entries=self.settings.history_max_entries,
        )
        self.overlay = OverlayWindow(
            width=self.settings.overlay_width,
            height=self.settings.overlay_height,
            opacity=self.settings.overlay_opacity,
        )
        self._latest_full_image: Image.Image | None = None
        self._latest_title: str = ""
        self._latest_hwnd: int = 0
        self._ocr_extractor = OCRTextExtractor(self.ocr)
        self._uia_extractor = UIAutomationTextExtractor()
        self._analyzing = False
        self._hotkey_was_down = False
        self._history_hotkey_was_down = False
        self._settings_hotkey_was_down = False
        self._freeze_hotkey_was_down = False
        self._settle_deadline: float | None = None
        self._ocr_ready = threading.Event()
        self._overlay_hwnd = 0
        self._monitor_hwnd = 0
        self._monitor_title = ""
        self.watcher = ContentWatcher(
            hash_provider=self._capture_hash,
            debounce_delay=self.settings.debounce_delay,
        )
        self._tray: TrayController | None = None
        self._last_confirmed_rect: tuple[int, int, int, int] | None = None
        self._confirmed_window_title: str = ""
        self._pending_change_while_frozen = False

    def _needs_region_confirm(self) -> bool:
        """当前窗口是否需要用户框选代码区域。"""
        if self._last_confirmed_rect is None:
            return True  # 从未选过
        # 窗口标题变了就重新选
        return self._latest_title != self._confirmed_window_title

    def run(self) -> None:
        """启动主循环。"""
        log.info("启动主循环")
        log.debug("配置: poll_interval=%s, debounce_delay=%s, stream=%s",
                   self.settings.poll_interval, self.settings.debounce_delay,
                   self.settings.stream_output)
        self.overlay.show_status(self._startup_message())
        self._arm_settle_deadline()
        self.overlay.set_poll_callback(
            int(self.settings.poll_interval * 1000),
            self._on_poll,
        )
        self._overlay_hwnd = self.overlay.hwnd
        self._start_hotkey_loop()
        if self.settings.tray_enabled:
            log.info("启动系统托盘")
            self._tray = TrayController(
                on_toggle=self._tray_toggle_overlay,
                on_freeze=self._tray_freeze_overlay,
                on_history=self._open_history_dialog,
                on_settings=self._open_settings_dialog,
                on_quit=self._request_shutdown,
                schedule=self.overlay.schedule,
            )
            self._tray.start()
        threading.Thread(target=self._warmup_ocr, daemon=True).start()
        try:
            self.overlay.mainloop()
        finally:
            log.info("主循环退出，清理资源")
            if self._tray is not None:
                self._tray.stop()
            self.ai.close()
            log.info("清理完成")

    def _startup_message(self) -> str:
        lines = [
            "Wanna Understanding 已启动",
            "正在监控活动窗口…",
            f"轮询间隔：{self.settings.poll_interval}s",
            f"防抖延迟：{self.settings.debounce_delay}s",
            f"局部发送：最多 {self.settings.context_max_lines} 行",
            f"AI 模型：{self.settings.deepseek_model}",
            f"识别模式：{'多模态视觉' if self.settings.use_vision else 'OCR 识别'}",
            "快捷键：Alt+Shift+H 显示/隐藏 | J 历史 | O 设置 | Alt+Shift+F 冻结",
            "悬浮窗：拖标题栏移动 | 拖蓝角/底边/右边缩放 | Ctrl+滚轮 | 双击标题",
        ]
        if self.settings.tray_enabled:
            lines.append("也可：托盘右键 → 设置 / 退出")
        if self.settings.stream_output:
            lines.append("AI 输出：流式")
        elif not self.settings.stream_output:
            lines.append("AI 输出：完整等待模式")
        if self.settings.auto_dark_theme:
            lines.append("深色主题：自动检测")
        if self.settings.monitor_mode == "custom":
            rect_hint = self.settings.monitor_rect or "未配置"
            lines.append(f"监控模式：自定义区域 ({rect_hint})")
        if self.settings.use_uia:
            lines.append("文本提取：UI Automation 优先")
        if self.settings.tray_enabled:
            lines.append("系统托盘：已启用（右键菜单可退出）")
        if not self.settings.has_api_key:
            lines.append("")
            lines.append("提示：未配置 DEEPSEEK_API_KEY，将仅展示 OCR 状态。")
        return "\n".join(lines)

    def _arm_settle_deadline(self) -> None:
        """在防抖迟迟不结束时，超时后强制用当前画面分析。"""
        wait = max(4.0, self.settings.debounce_delay * 3)
        self._settle_deadline = time.monotonic() + wait

    def _clear_settle_deadline(self) -> None:
        self._settle_deadline = None

    def _warmup_ocr(self) -> None:
        """后台预加载 EasyOCR，避免首次分析卡在「正在识别代码」。"""
        self._schedule_status("正在加载 OCR 模型（首次约 1–3 分钟，请稍候）…")
        try:
            self.ocr.warmup()
        except Exception as exc:
            self._schedule_status(
                f"OCR 加载失败：{exc}\n"
                "请运行：python scripts/ocr_download_models.py"
            )
            return
        self._ocr_ready.set()
        self._schedule_status(self._startup_message())

    def _on_poll(self) -> None:
        try:
            target = self._resolve_monitor_target()
            if target is None:
                if not self.overlay.is_frozen:
                    self.overlay.hide()
                return
            hwnd, title = target

            # 冻结期间：仅跟随窗口位置 + 检测窗口变化
            if self.overlay.is_frozen:
                if self.watcher.on_window_changed(hwnd):
                    self.cache.clear()
                    self._pending_change_while_frozen = True
                    log.info("窗口变化(冻结中): %s", title)
                region = self._build_capture_region(hwnd, title)
                rect = (
                    region.x, region.y,
                    region.x + region.width, region.y + region.height,
                )
                if self.overlay.is_visible:
                    self.overlay.show_near(rect)
                return

            if self.watcher.on_window_changed(hwnd):
                log.info("窗口切换: %s (hwnd=%d)", title, hwnd)
                self.cache.clear()
                self._arm_settle_deadline()
                self.overlay.show_status(
                    f"已切换窗口：{title}\n"
                    f"等待内容稳定…（停手约 {self.settings.debounce_delay}s）"
                )
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
                self._clear_settle_deadline()
                log.debug("内容已稳定，开始分析")
                self._start_analysis()
            elif (
                not self._analyzing
                and self._settle_deadline is not None
                and time.monotonic() >= self._settle_deadline
                and self._latest_full_image is not None
            ):
                self._clear_settle_deadline()
                log.debug("防抖超时，使用当前截图强制分析")
                self.overlay.show_status("画面仍在微动，使用当前截图继续分析…")
                self._start_analysis()
        except Exception as exc:
            log.error("轮询异常: %s", exc, exc_info=True)
            self.overlay.show_status(f"监控异常：{exc}")

    def _resolve_monitor_target(self) -> tuple[int, str] | None:
        """解析应监控的编辑器窗口；忽略本程序自己的悬浮窗/对话框。"""
        hwnd, title = get_foreground_window_info()
        if self._is_own_window(hwnd, title):
            if self._monitor_hwnd and is_window_visible(self._monitor_hwnd):
                return self._monitor_hwnd, self._monitor_title
            return None
        if not is_window_visible(hwnd):
            return None
        self._monitor_hwnd = hwnd
        self._monitor_title = title
        return hwnd, title

    def _is_own_window(self, hwnd: int, title: str) -> bool:
        if hwnd == self._overlay_hwnd:
            return True
        return title in {"Wanna Understanding", "设置"}

    def _start_hotkey_loop(self) -> None:
        """独立高频轮询快捷键（避免与屏幕轮询同频导致漏键）。"""

        def _loop() -> None:
            self._handle_hotkey()
            self.overlay.root.after(120, _loop)

        self.overlay.root.after(120, _loop)

    def _handle_hotkey(self) -> None:
        if self.settings.hotkey_toggle:
            pressed = hotkey_toggle_pressed()
            if pressed and not self._hotkey_was_down:
                visible = self.overlay.toggle_visibility()
                if not visible:
                    self.overlay.show_status("悬浮窗已隐藏（Alt+Shift+H 恢复）")
            self._hotkey_was_down = pressed

        history_pressed = hotkey_history_pressed()
        if history_pressed and not self._history_hotkey_was_down:
            self._open_history_dialog()
        self._history_hotkey_was_down = history_pressed

        settings_pressed = hotkey_settings_pressed()
        if settings_pressed and not self._settings_hotkey_was_down:
            self._open_settings_dialog()
        self._settings_hotkey_was_down = settings_pressed

        freeze_pressed = hotkey_freeze_pressed()
        if freeze_pressed and not self._freeze_hotkey_was_down:
            frozen = self.overlay.toggle_freeze()
            if frozen:
                self.overlay.show_status("内容已冻结（Alt+Shift+F 解冻）")
            else:
                if self._pending_change_while_frozen:
                    self._pending_change_while_frozen = False
                    self._arm_settle_deadline()
                    log.info("解冻后触发重新分析")
                self.overlay.show_status("内容已解冻，可接收新分析结果")
        self._freeze_hotkey_was_down = freeze_pressed

    def _open_history_dialog(self) -> None:
        HistoryDialog(
            self.overlay.root,
            self.history,
            on_select=lambda entry: self.overlay.update_content(entry.result),
        )

    def _open_settings_dialog(self) -> None:
        SettingsDialog(
            self.overlay.root,
            self.settings,
            on_saved=self._apply_settings,
        )

    def _tray_toggle_overlay(self) -> None:
        visible = self.overlay.toggle_visibility()
        if not visible:
            self.overlay.show_status("悬浮窗已隐藏（托盘或 Alt+Shift+H 恢复）")

    def _tray_freeze_overlay(self) -> None:
        """从托盘菜单切换冻结/解冻（绕过 hotkey）。"""
        frozen = self.overlay.toggle_freeze()
        log.info("托盘菜单切换冻结: %s", frozen)
        if not frozen and self._pending_change_while_frozen:
            self._pending_change_while_frozen = False
            self._arm_settle_deadline()
            log.info("解冻后触发重新分析")

    def _request_shutdown(self) -> None:
        if self._tray is not None:
            self._tray.stop()
            self._tray = None
        self.overlay.root.quit()

    def _apply_settings(self, new_settings: Settings) -> None:
        self.settings = new_settings
        self.ai.close()
        self.ai = AIClient(self.settings)
        self.watcher.debounce_delay = new_settings.debounce_delay
        self.history.set_max_entries(new_settings.history_max_entries)
        self.overlay.apply_geometry(
            new_settings.overlay_width,
            new_settings.overlay_height,
            new_settings.overlay_opacity,
        )
        self.overlay.set_poll_interval(int(new_settings.poll_interval * 1000))
        self._sync_tray()
        self.overlay.show_status("设置已更新并立即生效。")

    def _sync_tray(self) -> None:
        """按当前配置启动或停止系统托盘。"""
        if self.settings.tray_enabled:
            if self._tray is None:
                self._tray = TrayController(
                    on_toggle=self._tray_toggle_overlay,
                    on_freeze=self._tray_freeze_overlay,
                    on_history=self._open_history_dialog,
                    on_settings=self._open_settings_dialog,
                    on_quit=self._request_shutdown,
                    schedule=self.overlay.schedule,
                )
                self._tray.start()
            return
        if self._tray is not None:
            self._tray.stop()
            self._tray = None

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
        # 不要截图/分析自己的窗口（悬浮窗、设置对话框等）
        if self._is_own_window(hwnd, title):
            return ""
        self._latest_hwnd = hwnd
        self._latest_title = title
        # 截取完整窗口（不做中心裁剪，让用户在框选时看到全貌）
        # 用 mss 截取主显示器（避免 WindowRegion.physical_rect 重复 DPI 缩放）
        import mss
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            shot = sct.grab(monitor)
            image = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        self._latest_full_image = image
        log.debug("全屏截图: %dx%d", image.width, image.height)
        return ScreenCapturer.hash_image(image)
