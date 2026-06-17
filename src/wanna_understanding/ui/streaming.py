# SPDX-License-Identifier: AGPL-3.0

"""流式 UI 更新节流，避免 Tk 主线程被刷爆。"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable


class StreamUpdateThrottler:
    """合并高频流式更新，按最小间隔刷新 UI。"""

    def __init__(
        self,
        emit: Callable[[str], None],
        min_interval: float = 0.1,
    ) -> None:
        self._emit = emit
        self._min_interval = min_interval
        self._lock = threading.Lock()
        self._latest = ""
        self._last_emit = 0.0

    def push(self, text: str) -> None:
        """记录最新文本，必要时触发刷新。"""
        with self._lock:
            self._latest = text
        now = time.monotonic()
        if now - self._last_emit >= self._min_interval:
            self.flush()

    def flush(self) -> None:
        """立即刷新最新文本。"""
        with self._lock:
            text = self._latest
        self._last_emit = time.monotonic()
        self._emit(text)
