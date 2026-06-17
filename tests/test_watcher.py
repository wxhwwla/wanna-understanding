# SPDX-License-Identifier: AGPL-3.0

"""ContentWatcher 单元测试。"""

import time

from wanna_understanding.trigger.watcher import ContentWatcher


def test_watcher_returns_hash_after_settle(monkeypatch) -> None:
    values = iter(["h1", "h1", "h1"])
    watcher = ContentWatcher(hash_provider=lambda: next(values), debounce_delay=0.2)
    now = {"t": 0.0}
    monkeypatch.setattr(time, "monotonic", lambda: now["t"])
    assert watcher.poll() is None
    now["t"] = 0.3
    assert watcher.poll() == "h1"


def test_watcher_resets_on_window_change() -> None:
    watcher = ContentWatcher(hash_provider=lambda: "same", debounce_delay=0.1)
    assert watcher.on_window_changed(100) is True
    assert watcher.on_window_changed(100) is False
    watcher.reset()
    assert watcher.on_window_changed(200) is True
