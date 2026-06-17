# SPDX-License-Identifier: AGPL-3.0

"""Wanna Understanding — AI 代码审阅员。只读不写，零操作，实时分析。"""

from wanna_understanding.config import load_settings

__version__ = "0.1.8"
__all__: list[str] = [
    "__version__",
    "load_settings",
]
