# SPDX-License-Identifier: AGPL-3.0

"""Wanna Understanding — 主入口点（python -m wanna_understanding）。"""

from __future__ import annotations

import argparse
import sys

from wanna_understanding import __version__
from wanna_understanding.application import Application, run_smoke_test


def main(argv: list[str] | None = None) -> None:
    """启动 AI 代码审阅员主程序。"""
    parser = argparse.ArgumentParser(description="Wanna Understanding — AI 代码审阅员")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="无 GUI 冒烟测试：截图 → OCR → AI（打印到终端）",
    )
    args = parser.parse_args(argv)

    print(f"Wanna Understanding v{__version__}")
    if sys.platform != "win32":
        print("错误：当前仅支持 Windows。")
        sys.exit(1)

    if args.smoke:
        sys.exit(run_smoke_test())

    print("AI 代码审阅员 — 只读不写，零操作，实时分析")
    print()
    app = Application()
    app.run()


if __name__ == "__main__":
    main()
