# SPDX-License-Identifier: AGPL-3.0

"""无边框置顶悬浮窗，展示 AI 分析结果。"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import font as tkfont

from wanna_understanding.ai.cache import AnalysisResult
from wanna_understanding.screen.monitor import get_work_area_for_rect

from .position import compute_overlay_position


class OverlayWindow:
    """半透明置顶悬浮窗。"""

    def __init__(
        self,
        width: int = 400,
        height: int = 300,
        opacity: float = 0.85,
    ) -> None:
        self.width = width
        self.height = height
        self.opacity = opacity
        self._visible = True
        self.root = tk.Tk()
        self.root.title("Wanna Understanding")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", opacity)
        self.root.configure(bg="#1e1e1e")
        self._drag_offset = (0, 0)

        self._title = tk.Label(
            self.root,
            text="Wanna Understanding  (H/J/S: 隐藏/历史/设置)",
            bg="#1e1e1e",
            fg="#cccccc",
            font=tkfont.Font(family="Segoe UI", size=10, weight="bold"),
            anchor="w",
            padx=8,
            pady=4,
        )
        self._title.pack(fill="x")
        self._title.bind("<Button-1>", self._start_drag)
        self._title.bind("<B1-Motion>", self._on_drag)
        self._title.bind("<Double-Button-1>", lambda _e: self.toggle_visibility())

        self.text = tk.Text(
            self.root,
            wrap="word",
            bg="#2d2d2d",
            fg="#d4d4d4",
            font=tkfont.Font(family="Consolas", size=11),
            relief="flat",
            borderwidth=0,
            padx=8,
            pady=8,
        )
        self.text.pack(fill="both", expand=True)
        self.text.bind("<Button-1>", self._start_drag)
        self.text.bind("<B1-Motion>", self._on_drag)
        self.text.insert("end", "正在等待代码变化…")
        self.text.configure(state="disabled")
        self._poll_after_id: str | None = None
        self._poll_interval_ms = 2000
        self._poll_callback: Callable[[], None] | None = None

    @property
    def is_visible(self) -> bool:
        """悬浮窗是否处于显示状态。"""
        return self._visible

    def _start_drag(self, event: tk.Event) -> None:
        self._drag_offset = (
            event.x_root - self.root.winfo_x(),
            event.y_root - self.root.winfo_y(),
        )

    def _on_drag(self, event: tk.Event) -> None:
        x = event.x_root - self._drag_offset[0]
        y = event.y_root - self._drag_offset[1]
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")

    def show_near(self, window_rect: tuple[int, int, int, int]) -> None:
        """在目标窗口旁定位悬浮窗，空间不足时自动翻到左侧。"""
        work_area = get_work_area_for_rect(window_rect)
        x, y = compute_overlay_position(
            window_rect,
            self.width,
            self.height,
            work_area,
        )
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
        if self._visible:
            self.root.deiconify()

    def apply_geometry(self, width: int, height: int, opacity: float) -> None:
        """更新悬浮窗尺寸与透明度（立即生效）。"""
        self.width = max(200, width)
        self.height = max(150, height)
        self.opacity = max(0.1, min(1.0, opacity))
        self.root.attributes("-alpha", self.opacity)
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")

    def toggle_visibility(self) -> bool:
        """切换显示/隐藏，返回切换后是否可见。"""
        if self._visible:
            self.root.withdraw()
            self._visible = False
        else:
            self.root.deiconify()
            self._visible = True
        return self._visible

    def hide(self) -> None:
        """隐藏悬浮窗。"""
        self.root.withdraw()
        self._visible = False

    def show(self) -> None:
        """显示悬浮窗。"""
        self.root.deiconify()
        self._visible = True

    def update_content(self, result: AnalysisResult) -> None:
        """更新展示内容。"""
        self._set_text(result.format_display())

    def show_status(self, message: str) -> None:
        """显示状态信息。"""
        self._set_text(message)

    def show_streaming(self, partial: str) -> None:
        """流式展示 AI 回复片段。"""
        self._set_text(f"正在分析…\n\n{partial}")
        self.text.see("end")

    def schedule(self, callback: Callable[[], None]) -> None:
        """在主线程调度回调。"""
        self.root.after(0, callback)

    def _set_text(self, content: str) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("end", content)
        self.text.configure(state="disabled")

    def set_poll_callback(
        self, interval_ms: int, callback: Callable[[], None]
    ) -> None:
        """注册周期性轮询回调。"""
        self._poll_callback = callback
        self._poll_interval_ms = max(100, interval_ms)
        if self._poll_after_id is not None:
            self.root.after_cancel(self._poll_after_id)
            self._poll_after_id = None
        self._schedule_poll()

    def set_poll_interval(self, interval_ms: int) -> None:
        """运行时调整轮询间隔（毫秒）。"""
        self._poll_interval_ms = max(100, interval_ms)
        if self._poll_callback is None:
            return
        if self._poll_after_id is not None:
            self.root.after_cancel(self._poll_after_id)
            self._poll_after_id = None
        self._schedule_poll()

    def _schedule_poll(self) -> None:
        if self._poll_callback is None:
            return

        def _loop() -> None:
            if self._poll_callback is not None:
                self._poll_callback()
            self._poll_after_id = self.root.after(self._poll_interval_ms, _loop)

        self._poll_after_id = self.root.after(self._poll_interval_ms, _loop)

    def mainloop(self) -> None:
        """进入 Tk 主循环。"""
        self.root.mainloop()
