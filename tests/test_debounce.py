# SPDX-License-Identifier: AGPL-3.0

"""DebounceScheduler 单元测试。"""

import time

from wanna_understanding.trigger.debounce import DebounceScheduler


def test_debounce_fires_after_delay(monkeypatch) -> None:
    scheduler = DebounceScheduler(delay=0.5)
    now = {"t": 100.0}
    monkeypatch.setattr(time, "monotonic", lambda: now["t"])

    assert scheduler.observe("hash-a") is None
    now["t"] = 100.2
    assert scheduler.observe("hash-a") is None
    now["t"] = 100.6
    assert scheduler.observe("hash-a") == "hash-a"
    assert scheduler.observe("hash-a") is None


def test_debounce_reset_clears_state() -> None:
    scheduler = DebounceScheduler(delay=0.1)
    scheduler.reset()
    assert scheduler.observe("hash-b") is None
