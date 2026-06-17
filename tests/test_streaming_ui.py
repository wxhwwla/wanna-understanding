# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""StreamUpdateThrottler 测试。"""

import time

from wanna_understanding.ui.streaming import StreamUpdateThrottler


def test_throttler_emits_and_flushes_latest() -> None:
    emitted: list[str] = []
    throttler = StreamUpdateThrottler(emit=emitted.append, min_interval=0.2)
    throttler.push("a")
    assert emitted == ["a"]
    throttler.push("ab")
    throttler.push("abc")
    assert emitted == ["a"]
    time.sleep(0.25)
    throttler.push("abcd")
    assert emitted[-1] == "abcd"
    throttler.flush()
    assert emitted[-1] == "abcd"
