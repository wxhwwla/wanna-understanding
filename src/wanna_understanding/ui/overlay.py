# SPDX-License-Identifier: AGPL-3.0

"""无边框置顶悬浮窗，展示 AI 分析结果。"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import font as tkfont

from wanna_understanding.ai.cache import AnalysisResult


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
        self.root = tk.Tk()
        self.root.title("Wanna Understanding")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", opacity)
        self.root.configure(bg="#1e1e1e")
        self._drag_offset = (0, 0)

        self._title = tk.Label(
            self.root,
            text="Wanna Understanding",
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
        """在目标窗口右侧定位悬浮窗。"""
        _left, top, right, _bottom = window_rect
        x = right + 10
        y = top
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
        self.root.deiconify()

    def hide(self) -> None:
        """隐藏悬浮窗。"""
        self.root.withdraw()

    def update_content(self, result: AnalysisResult) -> None:
        """更新展示内容。"""
        self._set_text(result.format_display())

    def show_status(self, message: str) -> None:
        """显示状态信息。"""
        self._set_text(message)

    def schedule(self, callback: Callable[[], None]) -> None:
        """在主线程调度回调。"""
        self.root.after(0, callback)

    def _set_text(self, content: str) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("end", content)
        self.text.configure(state="disabled")

    def set_poll_callback(self, interval_ms: int, callback: Callable[[], None]) -> None:
        """注册周期性轮询回调。"""

        def _loop() -> None:
            callback()
            self.root.after(interval_ms, _loop)

        self.root.after(interval_ms, _loop)

    def mainloop(self) -> None:
        """进入 Tk 主循环。"""
        self.root.mainloop()
