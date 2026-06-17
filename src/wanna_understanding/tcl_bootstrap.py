# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""在导入 tkinter 之前修复 Windows 上 Tcl/Tk 路径，并启用 DPI 感知。"""

from __future__ import annotations

import os
import sys


def _ensure_dpi_aware() -> None:
    """启用 Windows DPI 感知，使 tkinter 窗口在 HiDPI 下正确缩放。

    必须在任何窗口创建前调用。否则 tkinter 的 fullscreen 窗口在 150%+ DPI
    下只占屏幕 2/3（逻辑分辨率），而不是完整物理屏幕。
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        # Vista+ 级别 DPI 感知：窗口使用物理像素
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

_ensure_dpi_aware()  # 模块加载时立即启用


def ensure_tcl_paths() -> None:
    r"""将 TCL_LIBRARY / TK_LIBRARY 指向 base_prefix\\tcl\\（若尚未设置）。"""
    if os.environ.get("TCL_LIBRARY"):
        return
    if sys.platform != "win32":
        return
    base = getattr(sys, "base_prefix", sys.prefix)
    tcl_dir = os.path.join(base, "tcl", "tcl8.6")
    tk_dir = os.path.join(base, "tcl", "tk8.6")
    if os.path.isfile(os.path.join(tcl_dir, "init.tcl")):
        os.environ["TCL_LIBRARY"] = tcl_dir
        os.environ["TK_LIBRARY"] = tk_dir


ensure_tcl_paths()
