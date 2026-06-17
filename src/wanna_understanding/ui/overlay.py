# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""无边框置顶悬浮窗，展示 AI 分析结果。"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import font as tkfont

from wanna_understanding import tcl_bootstrap as _tcl_bootstrap  # noqa: F401
from wanna_understanding.ai.cache import AnalysisResult
from wanna_understanding.logger import get_logger
from wanna_understanding.screen.monitor import get_work_area_for_rect

from .position import compute_overlay_position

_MIN_WIDTH = 280
_MIN_HEIGHT = 180
_RESIZE_CORNER = 28
_RESIZE_EDGE = 12
_TITLE_DEFAULT = "Wanna Understanding v0.1.17 · 拖标题栏移动 · 拖蓝角/底边/右边缩放"
_TITLE_FROZEN = "🧊 已冻结 · Alt+Shift+F 解冻"

log = get_logger(__name__)


class OverlayWindow:
    """半透明置顶悬浮窗。"""

    def __init__(
        self,
        width: int = 520,
        height: int = 380,
        opacity: float = 0.85,
    ) -> None:
        self.width = width
        self.height = height
        self.opacity = opacity
        self._visible = True
        self._frozen = False
        self._position_pinned = False
        self._drag_offset = (0, 0)
        self._resize_origin: tuple[int, int, int, int, int, int] = (0, 0, 0, 0, 0, 0)
        self._resize_mode = "se"
        self.root = tk.Tk()
        self.root.title("Wanna Understanding")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", opacity)
        self.root.configure(bg="#1e1e1e")
        # 启动时屏幕居中
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        sx = max(0, (sw - width) // 2)
        sy = max(0, (sh - height) // 2)
        self.root.geometry(f"{width}x{height}+{sx}+{sy}")

        # 内容区包含中英文混合（AI 分析结果 + 代码），不能只用 Consolas（无中文）
        # 使用 YaHei 可以正常显示中文，代码等宽不完美但替代乱码
        _title_font = tkfont.Font(family="Microsoft YaHei UI", size=12, weight="bold")
        if _title_font.measure("测") < 10:
            _title_font = tkfont.Font(family="Microsoft YaHei", size=12, weight="bold")
        _content_font = tkfont.Font(family="Microsoft YaHei", size=13)

        self._title = tk.Label(
            self.root,
            text=_TITLE_DEFAULT,
            bg="#1e1e1e",
            fg="#cccccc",
            font=_title_font,
            anchor="w",
            padx=8,
            pady=6,
            wraplength=max(240, width - 24),
        )
        self._title.pack(fill="x")
        self._bind_drag(self._title)
        self._title.bind("<Double-Button-1>", self._toggle_position_pin)
        self.root.bind("<Escape>", self._on_escape)

        self.text = tk.Text(
            self.root,
            wrap="word",
            bg="#2d2d2d",
            fg="#d4d4d4",
            font=_content_font,
            relief="flat",
            borderwidth=0,
            padx=8,
            pady=8,
        )
        self.text.pack(fill="both", expand=True)
        # 注意: 仅有标题栏可拖拽，Text 区域用于选择和阅读 — 蓝角/底边/右边专用缩放
        self.text.insert("end", "正在等待代码变化…")
        self.text.configure(state="disabled")

        self._edge_bottom = tk.Frame(
            self.root, bg="#4a4a4a", cursor="sb_v_double_arrow",
        )
        self._edge_bottom.place(
            relx=0, rely=1, relwidth=1, anchor="sw", height=_RESIZE_EDGE
        )
        self._bind_resize(self._edge_bottom, "s")

        self._edge_right = tk.Frame(self.root, bg="#4a4a4a", cursor="sb_h_double_arrow")
        self._edge_right.place(
            relx=1, rely=0, relheight=1, anchor="ne", width=_RESIZE_EDGE
        )
        self._bind_resize(self._edge_right, "e")

        self._corner = tk.Frame(self.root, bg="#4fc3f7", cursor="size_nw_se")
        self._corner.place(
            relx=1.0,
            rely=1.0,
            anchor="se",
            width=_RESIZE_CORNER,
            height=_RESIZE_CORNER,
        )
        self._bind_resize(self._corner, "se")
        self._corner.lift()
        self._edge_right.lift()
        self._edge_bottom.lift()

        self.root.bind("<Control-MouseWheel>", self._on_wheel_resize)
        self.root.bind(
            "<Control-Button-4>",
            lambda e: self._on_wheel_resize(e, delta=120),
        )
        self.root.bind(
            "<Control-Button-5>",
            lambda e: self._on_wheel_resize(e, delta=-120),
        )

        self._poll_after_id: str | None = None
        self._poll_interval_ms = 2000
        self._poll_callback: Callable[[], None] | None = None
        self.root.update_idletasks()

    @property
    def hwnd(self) -> int:
        """Windows 窗口句柄（用于忽略自身前台检测）。"""
        return int(self.root.winfo_id())

    @property
    def is_position_pinned(self) -> bool:
        """用户是否已手动固定位置/尺寸（不再跟随编辑器）。"""
        return self._position_pinned

    def _on_escape(self, _event: tk.Event) -> str:
        """Esc 不关闭程序，仅忽略（避免误触隐藏）。"""
        return "break"

    @property
    def is_visible(self) -> bool:
        """悬浮窗是否处于显示状态。"""
        return self._visible

    @property
    def is_frozen(self) -> bool:
        """悬浮窗内容是否已冻结（不再被新分析覆盖）。"""
        return self._frozen

    def toggle_freeze(self) -> bool:
        """切换冻结/解冻，返回冻结后的状态。

        冻结：保留当前显示内容不变，仅变标题栏颜色。
        解冻：恢复默认标题栏，下次结果更新时正常刷新。
        """
        self._frozen = not self._frozen
        state = "已冻结" if self._frozen else "已解冻"
        log.debug("悬浮窗%s", state)
        if self._frozen:
            self._title.configure(text=_TITLE_FROZEN, fg="#4fc3f7")
        else:
            self._restore_title()
        self._flash_title(f"内容{state}（Alt+Shift+F 切换）")
        return self._frozen

    def _bind_drag(self, widget: tk.Widget) -> None:
        widget.bind("<Button-1>", self._start_drag)
        widget.bind("<B1-Motion>", self._on_drag)
        widget.bind("<ButtonRelease-1>", self._on_drag_end)

    def _bind_resize(self, widget: tk.Widget, mode: str) -> None:
        widget.bind(
            "<Button-1>",
            lambda event, m=mode: self._start_resize(event, m),
        )
        widget.bind("<B1-Motion>", self._on_resize)
        widget.bind("<ButtonRelease-1>", self._on_resize_end)

    def _start_drag(self, event: tk.Event) -> None:
        log.debug("拖拽开始: x=%d, y=%d", event.x_root, event.y_root)
        self._drag_offset = (
            event.x_root - self.root.winfo_x(),
            event.y_root - self.root.winfo_y(),
        )

    def _on_drag(self, event: tk.Event) -> None:
        x = event.x_root - self._drag_offset[0]
        y = event.y_root - self._drag_offset[1]
        w = max(_MIN_WIDTH, self.root.winfo_width())
        h = max(_MIN_HEIGHT, self.root.winfo_height())
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _on_drag_end(self, _event: tk.Event) -> None:
        self._position_pinned = True
        self._sync_geometry_from_window()
        log.debug("拖拽结束，位置已固定")
        self._flash_title("位置已固定（双击标题恢复跟随）")

    def _start_resize(self, event: tk.Event, mode: str) -> None:
        log.debug("缩放开始: mode=%s, x=%d, y=%d", mode, event.x_root, event.y_root)
        self._resize_mode = mode
        self._sync_geometry_from_window()
        self._resize_origin = (
            event.x_root,
            event.y_root,
            self.width,
            self.height,
            self.root.winfo_x(),
            self.root.winfo_y(),
        )

    def _on_resize(self, event: tk.Event) -> None:
        sx, sy, sw, sh, ox, oy = self._resize_origin
        dx = event.x_root - sx
        dy = event.y_root - sy
        new_w = sw
        new_h = sh
        if self._resize_mode in {"se", "e"}:
            new_w = max(_MIN_WIDTH, sw + dx)
        if self._resize_mode in {"se", "s"}:
            new_h = max(_MIN_HEIGHT, sh + dy)
        log.debug("缩放中: %s → %dx%d (dx=%d, dy=%d)",
                   self._resize_mode, new_w, new_h, dx, dy)
        self.root.geometry(f"{new_w}x{new_h}+{ox}+{oy}")

    def _on_resize_end(self, _event: tk.Event) -> None:
        self._position_pinned = True
        self._sync_geometry_from_window()
        self._title.configure(wraplength=max(240, self.width - 24))
        log.debug("缩放结束: %dx%d", self.width, self.height)
        self._flash_title("尺寸已更新（双击标题恢复跟随）")

    def _on_wheel_resize(self, event: tk.Event, delta: int | None = None) -> str:
        """Ctrl + 滚轮缩放（备用）。"""
        step = delta if delta is not None else event.delta
        if step == 0:
            return "break"
        sign = 1 if step > 0 else -1
        self.width = max(_MIN_WIDTH, self.width + sign * 24)
        self.height = max(_MIN_HEIGHT, self.height + sign * 18)
        self._position_pinned = True
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
        self._title.configure(wraplength=max(240, self.width - 24))
        return "break"

    def _sync_geometry_from_window(self) -> None:
        self.root.update_idletasks()
        self.width = max(_MIN_WIDTH, self.root.winfo_width())
        self.height = max(_MIN_HEIGHT, self.root.winfo_height())

    def _toggle_position_pin(self, _event: tk.Event) -> None:
        self._position_pinned = not self._position_pinned
        if self._position_pinned:
            self._sync_geometry_from_window()
            self._flash_title("已固定位置（双击恢复跟随编辑器）")
        else:
            self._flash_title("已恢复跟随编辑器")

    def _flash_title(self, message: str) -> None:
        self._title.configure(text=message)
        self.root.after(2500, self._restore_title)

    def _restore_title(self) -> None:
        if self._frozen:
            self._title.configure(text=_TITLE_FROZEN, fg="#4fc3f7")
        else:
            self._title.configure(
                text=_TITLE_DEFAULT,
                wraplength=max(240, self.width - 24),
            )

    def show_near(self, window_rect: tuple[int, int, int, int]) -> None:
        """在目标窗口旁定位悬浮窗；用户固定位置后不再自动挪动。"""
        if self._visible:
            self.root.deiconify()
        if self._position_pinned:
            return
        work_area = get_work_area_for_rect(window_rect)
        x, y = compute_overlay_position(
            window_rect,
            self.width,
            self.height,
            work_area,
        )
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")

    def apply_geometry(self, width: int, height: int, opacity: float) -> None:
        """更新悬浮窗尺寸与透明度（立即生效）。"""
        self.width = max(_MIN_WIDTH, width)
        self.height = max(_MIN_HEIGHT, height)
        self.opacity = max(0.1, min(1.0, opacity))
        self.root.attributes("-alpha", self.opacity)
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
        self._title.configure(wraplength=max(240, self.width - 24))

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
        """更新展示内容（冻结时不更新）。"""
        if self._frozen:
            log.debug("内容更新被冻结跳过")
            return
        self._set_text(result.format_display())

    def show_status(self, message: str) -> None:
        """显示状态信息（冻结时不更新）。"""
        if self._frozen:
            return
        self._set_text(message)

    def show_streaming(self, partial: str) -> None:
        """流式展示 AI 回复片段（冻结时不更新）。"""
        if self._frozen:
            return
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
