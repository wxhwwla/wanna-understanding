# SPDX-License-Identifier: AGPL-3.0

"""Wanna Understanding — 主入口点（python -m wanna_understanding）。"""

from wanna_understanding import __version__


def main() -> None:
    """启动主程序。

    TODO: MVP 阶段 — 串联全模块（屏幕捕获 → OCR → AI → 悬浮窗）
    """
    print(f"Wanna Understanding v{__version__}")
    print("AI 代码审阅员 — 只读不写，零操作，实时分析")
    print()
    print("MVP 阶段：正在初始化各模块...")
    print()
    print("  [待实现] Screen Capturer  — mss + win32gui")
    print("  [待实现] OCR Engine       — PaddleOCR")
    print("  [待实现] AI Client        — DeepSeek API")
    print("  [待实现] Overlay Window   — tkinter 悬浮窗")
    print("  [待实现] Trigger Watcher  — 轮询 + 防抖")
    print()
    print('请先运行 pip install -e ".[dev]" 安装依赖后使用。')


if __name__ == "__main__":
    main()
