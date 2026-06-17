#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""项目版本号（从 _version.py 反向导入，保证单源）。"""

from __future__ import annotations

from scripts._version import _EXE_VERSION, _VERSION

__all__ = ["_EXE_VERSION", "_VERSION"]
