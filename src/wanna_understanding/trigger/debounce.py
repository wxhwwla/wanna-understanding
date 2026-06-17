# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""防抖调度器：内容稳定后再触发分析。"""

from __future__ import annotations

import time
from collections.abc import Callable


class DebounceScheduler:
    """在内容停止变化超过阈值后触发回调。"""

    def __init__(self, delay: float = 0.5) -> None:
        self._delay = delay
        self._pending_value: str | None = None
        self._changed_at: float = 0.0
        self._last_fired: str | None = None

    @property
    def delay(self) -> float:
        return self._delay

    @delay.setter
    def delay(self, value: float) -> None:
        self._delay = max(0.1, value)

    def observe(self, value: str) -> str | None:
        """记录新观测值；若已稳定且与上次触发不同则返回该值。"""
        now = time.monotonic()
        if value != self._pending_value:
            self._pending_value = value
            self._changed_at = now
            return None
        if value == self._last_fired:
            return None
        if now - self._changed_at < self._delay:
            return None
        self._last_fired = value
        return value

    def reset(self) -> None:
        """清空防抖状态（例如窗口切换时）。"""
        self._pending_value = None
        self._changed_at = 0.0
        self._last_fired = None

    def on_settled(self, value: str, callback: Callable[[str], None]) -> bool:
        """若 value 已稳定则执行回调并返回 True。"""
        settled = self.observe(value)
        if settled is None:
            return False
        callback(settled)
        return True
