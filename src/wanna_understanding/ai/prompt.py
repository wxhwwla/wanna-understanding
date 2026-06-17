# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""Prompt 模板：系统角色与用户消息构建。"""

from __future__ import annotations

SYSTEM_PROMPT = """你是一个资深的代码审阅员。
你的任务是分析用户提供的代码片段，并给出结构化的反馈。

注意：
1. 只分析代码，不要评价代码风格或格式
2. 如果代码有严重错误或潜在 bug，请明确指出
3. 如果代码正确但可以改进，给出具体建议
4. 如果看不出功能或无法分析（如代码过于碎片化），直接说“无法确定”
5. 保持简洁，每个部分不超过3句话"""


def build_user_prompt(code: str) -> str:
    """构建发送给 AI 的用户 Prompt。"""
    return (
        "请分析以下代码：\n\n"
        f"```\n{code}\n```\n\n"
        "请按以下格式回复：\n"
        "功能说明：[一段话概括这段代码的功能]\n"
        '潜在 Bug：[列出可能的 bug 或逻辑错误；无则写"未发现明显 bug"]\n'
        '改进建议：[列出改进建议；无则写"暂无"]'
    )
