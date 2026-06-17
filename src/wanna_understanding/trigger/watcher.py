# SPDX-License-Identifier: AGPL-3.0

"""内容变化监控：轮询截图哈希并在稳定后触发分析。"""

from __future__ import annotations

from collections.abc import Callable

from .debounce import DebounceScheduler


class ContentWatcher:
    """监控目标窗口截图哈希，防抖后通知内容已稳定。"""

    def __init__(
        self,
        hash_provider: Callable[[], str],
        debounce_delay: float = 0.5,
    ) -> None:
        self._hash_provider = hash_provider
        self._debounce = DebounceScheduler(delay=debounce_delay)
        self._last_hwnd: int | None = None

    def poll(self) -> str | None:
        """轮询一次；若内容已稳定且发生变化则返回新的内容哈希。"""
        return self._debounce.observe(self._hash_provider())

    def on_window_changed(self, hwnd: int) -> bool:
        """活动窗口切换时重置状态，返回是否发生了切换。"""
        if hwnd == self._last_hwnd:
            return False
        self._last_hwnd = hwnd
        self._debounce.reset()
        return True

    def reset(self) -> None:
        """重置监控状态。"""
        self._last_hwnd = None
        self._debounce.reset()
