# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""AIClient 解析逻辑测试。"""

from wanna_understanding.ai.client import AIClient
from wanna_understanding.config import Settings


def test_parse_structured_response() -> None:
    client = AIClient(Settings(deepseek_api_key=""))
    raw = "功能说明：计算列表元素之和\n潜在 Bug：未处理空列表\n改进建议：添加类型注解"
    parsed = client._parse_response(raw)
    assert parsed["summary"] == "计算列表元素之和"
    assert parsed["bugs"] == ["未处理空列表"]
    assert parsed["suggestions"] == ["添加类型注解"]


def test_analyze_without_api_key_returns_hint() -> None:
    client = AIClient(Settings(deepseek_api_key=""))
    result = client.analyze("def foo():\n    return 1")
    assert "DEEPSEEK_API_KEY" in result.summary
