#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""屏幕区域框选工具：拖拽选定监控矩形并打印环境变量。"""

from __future__ import annotations

from wanna_understanding.screen.custom_region import format_monitor_rect
from wanna_understanding.screen.region_picker import pick_screen_region


def main() -> int:
    """全屏半透明遮罩，拖拽框选后输出 WU_MONITOR_RECT。"""
    result = pick_screen_region()
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
