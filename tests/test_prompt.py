# SPDX-License-Identifier: AGPL-3.0

"""Prompt 构建测试。"""

from wanna_understanding.ai.prompt import build_user_prompt


def test_build_user_prompt_contains_code_block() -> None:
    prompt = build_user_prompt("print('hi')")
    assert "print('hi')" in prompt
    assert "功能说明" in prompt
