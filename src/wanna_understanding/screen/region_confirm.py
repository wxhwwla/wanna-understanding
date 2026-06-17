# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""全屏截图 + 手动框选代码区域：用户拖动选择，所见即所得。"""

from __future__ import annotations

import tkinter as tk
from contextlib import suppress
from typing import TYPE_CHECKING

from wanna_understanding.logger import get_logger

if TYPE_CHECKING:
    from PIL import Image

log = get_logger(__name__)


def select_code_region(screenshot: Image.Image) -> tuple[int, int, int, int] | None:
    """全屏显示截图，用户拖动框选代码区域。

    Args:
        screenshot: 原始截图

    Returns:
        (left, top, right, bottom) 像素坐标，或 None（取消）
    """
    import numpy as np
    from PIL import Image as PILImage
    from PIL import ImageTk

    root = tk.Toplevel()
    root.title("选择代码区域")
    root.attributes("-fullscreen", True)
    root.attributes("-topmost", True)
    root.configure(bg="black")
    root.grab_set()
    root.focus_force()
    root.update_idletasks()

    # Canvas 铺满全屏
    canvas = tk.Canvas(root, bg="black", highlightthickness=0, cursor="cross")
    canvas.pack(fill=tk.BOTH, expand=True)
    root.update_idletasks()
    canvas.update_idletasks()
    cw = canvas.winfo_width()
    ch = canvas.winfo_height()

    # 截图尺寸（物理像素），缩放到 Canvas 逻辑尺寸
    margin = 20  # 逻辑像素边距
    img_w, img_h = screenshot.size
    avail_w = cw - margin * 2
    avail_h = ch - margin * 2
    scale = min(avail_w / img_w, avail_h / img_h, 1.0)
    disp_w = max(1, int(img_w * scale))
    disp_h = max(1, int(img_h * scale))

    # 显示暗化截图
    arr = np.asarray(screenshot.convert("RGB"), dtype=np.uint8)
    arr = (arr * 0.3).astype(np.uint8)
    preview = PILImage.fromarray(arr).resize(
        (disp_w, disp_h), PILImage.Resampling.LANCZOS,
    )
    tk_img = ImageTk.PhotoImage(preview)

    # 在 Canvas 正中心绘制图片（所有坐标在 Canvas 逻辑空间内）
    img_id = canvas.create_image(cw // 2, ch // 2, anchor=tk.CENTER, image=tk_img)

    # 用 bbox 获取图片的实际边界
    canvas.update_idletasks()
    bbox = canvas.bbox(img_id)
    if bbox and len(bbox) == 4:
        _img_left, _img_top, _ign_r, _ign_b = bbox
    else:
        _img_left = (cw - disp_w) // 2
        _img_top = (ch - disp_h) // 2

    log.debug("界面: 画布=%dx%d 截图物理=%dx%d scale=%.2f img=(%d,%d)",
              cw, ch, img_w, img_h, scale, _img_left, _img_top)

    # 选框状态
    drag_start: tuple[int, int] | None = None
    sel_rect_id: int | None = None
    result: tuple[int, int, int, int] | None = None

    def _to_img(px: int, py: int) -> tuple[int, int]:
        """画布坐标 → 截图像素坐标。"""
        img_x = (px - _img_left) / (disp_w / img_w)
        img_y = (py - _img_top) / (disp_h / img_h)
        return (
            max(0, min(img_w, int(img_x))),
            max(0, min(img_h, int(img_y))),
        )

    def _on_press(ev: tk.Event) -> None:
        nonlocal drag_start, sel_rect_id
        # 清除旧选框
        if sel_rect_id is not None:
            with suppress(Exception):
                canvas.delete(sel_rect_id)
            sel_rect_id = None
        drag_start = (ev.x, ev.y)

    def _on_drag(ev: tk.Event) -> None:
        nonlocal sel_rect_id
        if drag_start is None:
            return
        if sel_rect_id is None:
            sel_rect_id = canvas.create_rectangle(
                drag_start[0], drag_start[1], ev.x, ev.y,
                outline="#00ff88", width=2,
            )
        else:
            canvas.coords(sel_rect_id, drag_start[0], drag_start[1], ev.x, ev.y)

    def _on_release(ev: tk.Event) -> None:
        """松手时啥也不做，仅确保选框已绘制。用户按 Enter 才确认。"""
        if drag_start is None:
            return
        x0, y0 = drag_start
        x1, y1 = ev.x, ev.y
        if abs(x1 - x0) < 20 or abs(y1 - y0) < 20:
            return
        if sel_rect_id:
            canvas.coords(sel_rect_id, x0, y0, x1, y1)
        log.debug("选框完成: (%d,%d)-(%d,%d)", x0, y0, x1, y1)

    def _confirm_sel() -> None:
        nonlocal result
        if sel_rect_id is None:
            return
        coords = canvas.coords(sel_rect_id)
        if len(coords) != 4:
            return
        x0, y0, x1, y1 = map(int, coords)
        if abs(x1 - x0) < 20 or abs(y1 - y0) < 20:
            return
        ix0, iy0 = _to_img(min(x0, x1), min(y0, y1))
        ix1, iy1 = _to_img(max(x0, x1), max(y0, y1))
        result = (ix0, iy0, ix1, iy1)
        log.info("用户确认框选: (%d,%d,%d,%d) = %dx%d",
                  ix0, iy0, ix1, iy1, ix1 - ix0, iy1 - iy0)
        root.destroy()

    def _cancel(_ev: tk.Event | None = None) -> None:
        root.destroy()

    canvas.bind("<ButtonPress-1>", _on_press)
    canvas.bind("<B1-Motion>", _on_drag)
    canvas.bind("<ButtonRelease-1>", _on_release)
    root.bind("<Return>", lambda _: _confirm_sel())
    root.bind("<Escape>", _cancel)

    # 顶部提示
    tk.Label(
        root,
        text="🖱 按住拖动框选代码区域（绿色选框） · Enter 确认 · Esc 取消",
        fg="white", bg="black",
        font=("Microsoft YaHei", 13),
    ).place(relx=0.5, rely=0.01, anchor="n")

    # 底部按钮
    btn_font = ("Microsoft YaHei", 12)
    btn_y = ch - 55
    tk.Button(
        root, text="✅ 确认 (Enter)", command=_confirm_sel,
        font=btn_font, bg="#2d2d2d", fg="#00ff88",
    ).place(x=cw // 2 - 180, y=btn_y, width=160)
    tk.Button(
        root, text="❌ 取消 (Esc)", command=_cancel,
        font=btn_font, bg="#2d2d2d", fg="#ff6666",
    ).place(x=cw // 2 + 20, y=btn_y, width=160)

    root.wait_window()
    return result
