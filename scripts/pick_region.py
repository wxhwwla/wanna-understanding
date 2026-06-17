#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0

"""屏幕区域框选工具：拖拽选定监控矩形并打印环境变量。"""

from __future__ import annotations

import tkinter as tk

from wanna_understanding.screen.custom_region import (
    ScreenRect,
    format_monitor_rect,
)


def main() -> int:
    """全屏半透明遮罩，拖拽框选后输出 WU_MONITOR_RECT。"""
    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", 0.25)
    root.configure(bg="black")
    root.attributes("-topmost", True)

    canvas = tk.Canvas(root, cursor="cross", highlightthickness=0, bg="black")
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
                x0,
                y0,
                x1,
                y1,
                outline="#00ff88",
                width=2,
            )
        else:
            canvas.coords(rect_id, x0, y0, x1, y1)

    def on_release(event: tk.Event) -> None:
        nonlocal result
        if start is None:
            return
        x0, y0 = start
        x1, y1 = event.x_root, event.y_root
        left = min(x0, x1)
        top = min(y0, y1)
        width = abs(x1 - x0)
        height = abs(y1 - y0)
        if width < 10 or height < 10:
            return
        result = ScreenRect(x=left, y=top, width=width, height=height)
        root.quit()

    def on_escape(_event: tk.Event | None = None) -> None:
        root.quit()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.bind("<Escape>", on_escape)

    label = tk.Label(
        root,
        text="拖拽框选监控区域，Esc 取消",
        fg="white",
        bg="black",
        font=("Segoe UI", 14),
    )
    label.place(relx=0.5, rely=0.02, anchor="n")

    root.mainloop()
    root.destroy()

    if result is None:
        print("已取消框选。")
        return 1

    formatted = format_monitor_rect(result)
    print("框选完成，请将以下配置写入 .env 或环境变量：")
    print("WU_MONITOR_MODE=custom")
    print(f"WU_MONITOR_RECT={formatted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
