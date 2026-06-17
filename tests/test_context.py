# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""trim_to_context 单元测试。"""

from wanna_understanding.ai.context import trim_to_context


def test_trim_keeps_short_code() -> None:
    code = "line1\nline2\nline3"
    assert trim_to_context(code, max_lines=20) == code


def test_trim_takes_middle_window() -> None:
    lines = [f"line{i}" for i in range(30)]
    code = "\n".join(lines)
    trimmed = trim_to_context(code, max_lines=10)
    assert trimmed.splitlines() == [f"line{i}" for i in range(10, 20)]
