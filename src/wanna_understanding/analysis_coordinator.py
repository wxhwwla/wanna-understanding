# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""分析协调模块：提取 application.py 的分析工作流，降低文件长度。"""

from __future__ import annotations

import hashlib
import threading
import time
import traceback

from PIL import Image

from wanna_understanding.ai.cache import AnalysisResult
from wanna_understanding.ai.context import trim_to_context
from wanna_understanding.logger import get_logger
from wanna_understanding.ocr.profiles import detect_editor_profile
from wanna_understanding.screen.text_extract import extract_code_text
from wanna_understanding.ui.streaming import StreamUpdateThrottler

log = get_logger(__name__)


class AnalysisCoordinator:
    """分析协调混入，为 Application 提供分析工作流方法。"""

    # ── 以下方法由 Application 提供 ──
    # self.overlay, self.settings, self.cache, self.history, self.ai
    # self._ocr_ready, self._latest_full_image, self._latest_title
    # self._latest_hwnd, self._analyzing, self._last_confirmed_rect
    # self._confirmed_window_title, self._ocr_extractor, self._uia_extractor

    def _warmup_ocr(self) -> None:
        """后台预加载 EasyOCR，避免首次分析卡在「正在识别代码」。"""
        self._schedule_status("正在加载 OCR 模型（首次约 1–3 分钟，请稍候）…")
        try:
            self.ocr.warmup()  # type: ignore[attr-defined]
        except Exception as exc:
            self._schedule_status(
                f"OCR 加载失败：{exc}\n"
                "请运行：python scripts/ocr_download_models.py"
            )
            return
        self._ocr_ready.set()  # type: ignore[attr-defined]
        self._schedule_status(self._startup_message())  # type: ignore[attr-defined]

    def _resolve_dark_theme(self, image: Image.Image, profile_name: str) -> bool:
        if profile_name.endswith("_dark"):
            return True
        if profile_name.endswith("_light"):
            return False
        if self.settings.auto_dark_theme:  # type: ignore[attr-defined]
            from wanna_understanding.ocr.theme import detect_dark_theme

            return detect_dark_theme(image)
        return self.settings.dark_theme  # type: ignore[attr-defined]

    def _start_analysis(self) -> None:
        if self._latest_full_image is None:  # type: ignore[attr-defined]
            log.debug("跳过分析: 无可用截图")
            return
        self._analyzing = True  # type: ignore[attr-defined]
        log.info("=== 开始分析 ===")
        if not self._ocr_ready.is_set():  # type: ignore[attr-defined]
            self.overlay.show_status("正在加载 OCR 模型，请稍候…")  # type: ignore[attr-defined]
        else:
            self.overlay.show_status("正在识别代码…")  # type: ignore[attr-defined]

        # === 主线程：完整窗口截图 → 用户手动框选 ===
        raw = self._latest_full_image.copy()  # type: ignore[attr-defined]
        # 窗口切换后重新框选；同一窗口复用上次的选择
        need_selection = self._needs_region_confirm()  # type: ignore[attr-defined]
        if need_selection:
            from wanna_understanding.screen.region_confirm import select_code_region

            overlay_was_visible = self.overlay.is_visible  # type: ignore[attr-defined]
            self.overlay.hide()  # type: ignore[attr-defined]
            self.overlay.show_status("请在截图框选代码区域…")  # type: ignore[attr-defined]
            sel_rect = select_code_region(raw)
            if sel_rect is None:
                log.info("用户取消了区域选择")
                if overlay_was_visible:
                    self.overlay.show()  # type: ignore[attr-defined]
                self._analyzing = False  # type: ignore[attr-defined]
                return
            self._last_confirmed_rect = sel_rect  # type: ignore[attr-defined]
            self._confirmed_window_title = self._latest_title  # type: ignore[attr-defined]
            crop_rect = sel_rect
            log.info("用户选择代码区域: (%d,%d,%d,%d) 窗口=%s",
                      *crop_rect, self._latest_title)  # type: ignore[attr-defined]
            if overlay_was_visible:
                self.overlay.show()  # type: ignore[attr-defined]
        else:
            # 复用上次框选区域
            crop_rect = self._last_confirmed_rect  # type: ignore[unreachable]
            log.debug("复用上次区域: (%d,%d,%d,%d)", *crop_rect)
            assert crop_rect is not None

        code_image = raw.crop(crop_rect)
        log.debug("最终代码区域: (%d,%d,%d,%d) → %dx%d",
                  *crop_rect, code_image.width, code_image.height)

        # === 后台线程：OCR + AI（或纯视觉 AI） ===
        def work(img: Image.Image = code_image) -> None:
            stop_heartbeat = threading.Event()
            started = time.monotonic()
            phase: list[str] = ["vision" if self.settings.use_vision  # type: ignore[attr-defined]
                                else "OCR"]

            def heartbeat() -> None:
                while not stop_heartbeat.wait(3.0):
                    elapsed = int(time.monotonic() - started)
                    label = {
                        "vision": "AI 正在分析截图",
                        "AI": "正在调用 AI 分析",
                        "OCR": "正在识别代码",
                    }.get(phase[0], "正在分析")
                    self._schedule_status(f"{label}…（已 {elapsed}s）")

            pulse = threading.Thread(target=heartbeat, daemon=True)
            pulse.start()
            try:
                # ── 多模态视觉模式：跳过 OCR，直接发截图给 AI ──
                if self.settings.use_vision:  # type: ignore[attr-defined]
                    log.info("多模态视觉模式：直接分析截图")
                    result = self.ai.analyze_vision(img)  # type: ignore[attr-defined]
                    self._schedule_result(result)
                    self._schedule_freeze()
                    log.info("视觉分析完成")
                    return

                # ── OCR 模式：现有流程 ──
                if not self._ocr_ready.is_set():  # type: ignore[attr-defined]
                    log.info("首次 OCR 预热中…")
                    self.ocr.warmup()  # type: ignore[attr-defined]
                    self._ocr_ready.set()  # type: ignore[attr-defined]
                    log.info("OCR 预热完成")
                profile = detect_editor_profile(
                    self._latest_title,  # type: ignore[attr-defined]
                    img,
                    auto_dark_theme=self.settings.auto_dark_theme,  # type: ignore[attr-defined]
                    forced=self.settings.editor_profile,  # type: ignore[attr-defined]
                )
                is_dark = self._resolve_dark_theme(img, profile.name)
                log.debug("编辑器配置: %s, 深色模式: %s", profile.name, is_dark)
                code = extract_code_text(
                    hwnd=self._latest_hwnd,  # type: ignore[attr-defined]
                    image=img,
                    use_uia=self.settings.use_uia,  # type: ignore[attr-defined]
                    ocr=self._ocr_extractor,  # type: ignore[attr-defined]
                    uia=self._uia_extractor,  # type: ignore[attr-defined]
                    window_title=self._latest_title,  # type: ignore[attr-defined]
                    profile=profile,
                    is_dark_theme=is_dark,
                )
                if not code.strip():
                    log.warning("OCR 未识别到有效代码")
                    self._schedule_status(
                        "未识别到有效代码，请确保编辑器中有可见代码。"
                    )
                    return
                log.debug("OCR 提取到 %d 字符", len(code))
                trimmed = trim_to_context(code, self.settings.context_max_lines)  # type: ignore[attr-defined]
                code_hash = hashlib.sha256(trimmed.encode("utf-8")).hexdigest()
                cached = self.cache.get(code_hash)  # type: ignore[attr-defined]
                if cached:
                    log.info("缓存命中: %s...", code_hash[:8])
                    self._record_history(trimmed, cached)
                    self._schedule_result(cached)
                    self._schedule_freeze()
                    return
                log.info("缓存未命中，调用 AI 分析")
                phase[0] = "AI"
                result = self._run_ai_analysis(trimmed, code_hash)
                self.cache.put(code_hash, result)  # type: ignore[attr-defined]
                self._record_history(trimmed, result)
                self._schedule_result(result)
                self._schedule_freeze()
                log.info("分析完成")
            except Exception as exc:
                detail = traceback.format_exc(limit=2)
                log.error("分析失败: %s", exc, exc_info=True)
                self._schedule_status(f"分析失败：{exc}\n\n{detail}")
            finally:
                stop_heartbeat.set()
                self._analyzing = False  # type: ignore[attr-defined]

        threading.Thread(target=work, daemon=True).start()

    def _run_ai_analysis(self, code: str, code_hash: str) -> AnalysisResult:
        """调用 AI；流式模式下边生成边刷新悬浮窗。"""
        if not self.settings.stream_output:  # type: ignore[attr-defined]
            self._schedule_status("正在调用 AI 分析…")
            return self.ai.analyze(code, code_hash=code_hash)  # type: ignore[attr-defined]

        throttler = StreamUpdateThrottler(
            emit=lambda text: self.overlay.schedule(  # type: ignore[attr-defined]
                lambda t=text: self.overlay.show_streaming(t)  # type: ignore[attr-defined]
            ),
            min_interval=self.settings.stream_ui_interval,  # type: ignore[attr-defined]
        )

        def on_delta(_delta: str, accumulated: str) -> None:
            throttler.push(accumulated)

        self.overlay.schedule(lambda: self.overlay.show_streaming(""))  # type: ignore[attr-defined]
        result = self.ai.analyze_stream(  # type: ignore[attr-defined]
            code,
            on_delta=on_delta,
            code_hash=code_hash,
        )
        throttler.flush()
        return result

    def _schedule_status(self, message: str) -> None:
        log.debug("状态: %s", message.split("\n")[0])
        self.overlay.schedule(lambda: self.overlay.show_status(message))  # type: ignore[attr-defined]

    def _schedule_result(self, result: AnalysisResult) -> None:
        self.overlay.schedule(lambda: self.overlay.update_content(result))  # type: ignore[attr-defined]

    def _schedule_freeze(self) -> None:
        """分析完成后延迟 2 秒自动冻结（让流式显示稳定后再冻结）。"""
        def _do_freeze() -> None:
            self.overlay.toggle_freeze()  # type: ignore[attr-defined]
        # 延迟 2 秒，避免流式更新还在进行就被冻结截断
        self.overlay.root.after(2000, _do_freeze)  # type: ignore[attr-defined]

    def _record_history(self, code: str, result: AnalysisResult) -> None:
        if not self.settings.history_enabled:  # type: ignore[attr-defined]
            return
        self.history.append(  # type: ignore[attr-defined]
            window_title=self._latest_title,  # type: ignore[attr-defined]
            code=code,
            result=result,
        )
