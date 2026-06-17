# SPDX-License-Identifier: AGPL-3.0

"""在导入 tkinter 之前修复 Windows 上 Tcl/Tk 路径。"""

from __future__ import annotations

import os
import sys


def ensure_tcl_paths() -> None:
    """将 TCL_LIBRARY / TK_LIBRARY 指向 base_prefix\\tcl\\（若尚未设置）。"""
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
