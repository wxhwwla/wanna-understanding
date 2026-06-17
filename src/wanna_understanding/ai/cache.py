# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""AI 分析结果模型与 LRU 缓存。"""

from __future__ import annotations

import time
from collections import OrderedDict

from pydantic import BaseModel, Field


class AnalysisResult(BaseModel):
    """结构化 AI 分析结果。"""

    code_hash: str
    summary: str
    bugs: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    raw_response: str = ""
    timestamp: float = Field(default_factory=time.time)

    def format_display(self) -> str:
        """格式化为悬浮窗展示文本。"""
        lines = [f"功能说明：{self.summary}", ""]
        lines.append("潜在 Bug：")
        if self.bugs:
            lines.extend(f"  • {bug}" for bug in self.bugs)
        else:
            lines.append("  • 未发现明显 bug")
        lines.append("")
        lines.append("改进建议：")
        if self.suggestions:
            lines.extend(f"  • {item}" for item in self.suggestions)
        else:
            lines.append("  • 暂无")
        if "无法确定" in self.summary and self.raw_response.strip():
            lines.extend(
                [
                    "",
                    "—— 原始回复 ——",
                    self.raw_response.strip()[:800],
                ]
            )
        return "\n".join(lines).strip()


class ResultCache:
    """基于 LRU 策略的 AI 结果缓存。"""

    def __init__(self, max_size: int = 100) -> None:
        self._max_size = max_size
        self._cache: OrderedDict[str, AnalysisResult] = OrderedDict()

    def get(self, code_hash: str) -> AnalysisResult | None:
        """获取缓存的分析结果。"""
        if code_hash not in self._cache:
            return None
        self._cache.move_to_end(code_hash)
        return self._cache[code_hash]

    def put(self, code_hash: str, result: AnalysisResult) -> None:
        """写入分析结果；超出容量时淘汰最久未使用项。"""
        self._cache[code_hash] = result
        self._cache.move_to_end(code_hash)
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def clear(self) -> None:
        """清空缓存。"""
        self._cache.clear()

    def __len__(self) -> int:
        """返回缓存条目数量。"""
        return len(self._cache)
