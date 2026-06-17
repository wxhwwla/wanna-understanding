# SPDX-License-Identifier: AGPL-3.0

"""Wanna Understanding — 主入口点（python -m wanna_understanding）。"""

from __future__ import annotations

import sys

from wanna_understanding import __version__
from wanna_understanding.application import Application


def main() -> None:
    """启动 AI 代码审阅员主程序。"""
    print(f"Wanna Understanding v{__version__}")
    print("AI 代码审阅员 — 只读不写，零操作，实时分析")
    print()
    if sys.platform != "win32":
        print("错误：MVP 当前仅支持 Windows。")
        sys.exit(1)
    app = Application()
    app.run()


if __name__ == "__main__":
    main()
