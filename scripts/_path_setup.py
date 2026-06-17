#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""路径设置 — 确保仓库根目录在 sys.path 中。"""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_root() -> None:
    """将仓库根目录加入 sys.path（如尚未存在）。"""
    root = Path(__file__).resolve().parent.parent
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
