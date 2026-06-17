# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""全屏框选监控区域（供设置对话框与 CLI 复用）。"""

from __future__ import annotations

import tkinter as tk

from .custom_region import ScreenRect


def pick_screen_region(parent: tk.Misc | None = None) -> ScreenRect | None:
    """拖拽框选屏幕矩形；Esc 取消返回 None。"""
    owns_root = parent is None
    if owns_root:
        root = tk.Tk()
        root.withdraw()
        picker = tk.Toplevel(root)
    else:
        root = parent.winfo_toplevel()
        picker = tk.Toplevel(parent)
    picker.title("框选监控区域")
    picker.attributes("-fullscreen", True)
    picker.attributes("-alpha", 0.25)
    picker.configure(bg="black")
    picker.attributes("-topmost", True)
    picker.grab_set()

    canvas = tk.Canvas(picker, cursor="cross", highlightthickness=0, bg="black")
    canvas.pack(fill=tk.BOTH, expand=True)

    start: tuple[int, int] | None = None
    rect_id: int | None = None
    result: ScreenRect | None = None

    def on_press(event: tk.Event) -> None:
        nonlocal start, rect_id
        start = (event.x_root, event.y_root)
        if rect_id is not None:
            canvas.delete(rect_id)
            rect_id = None

    def on_drag(event: tk.Event) -> None:
        nonlocal rect_id
        if start is None:
            return
        x0, y0 = start
        x1, y1 = event.x_root, event.y_root
        if rect_id is None:
            rect_id = canvas.create_rectangle(
                x0, y0, x1, y1, outline="#00ff88", width=2
            )
        else:
            canvas.coords(rect_id, x0, y0, x1, y1)

    def on_release(event: tk.Event) -> None:
        nonlocal result
        if start is None:
            return
        x0, y0 = start
        x1, y1 = event.x_root, event.y_root
        width = abs(x1 - x0)
        height = abs(y1 - y0)
        if width < 10 or height < 10:
            return
        result = ScreenRect(
            x=min(x0, x1),
            y=min(y0, y1),
            width=width,
            height=height,
        )
        picker.destroy()

    def on_escape(_event: tk.Event | None = None) -> None:
        picker.destroy()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    picker.bind("<Escape>", on_escape)

    label = tk.Label(
        picker,
        text="拖拽框选监控区域，Esc 取消",
        fg="white",
        bg="black",
        font=("Segoe UI", 14),
    )
    label.place(relx=0.5, rely=0.02, anchor="n")

    picker.wait_window()
    if owns_root:
        root.destroy()
    return result
