# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""AI 分析模块。"""

from .cache import AnalysisResult, ResultCache
from .client import AIClient
from .context import trim_to_context
from .history import HistoryEntry, HistoryStore
from .prompt import SYSTEM_PROMPT, build_user_prompt
from .stream import extract_delta_from_chunk, parse_sse_data_payload

__all__ = [
    "SYSTEM_PROMPT",
    "AIClient",
    "AnalysisResult",
    "HistoryEntry",
    "HistoryStore",
    "ResultCache",
    "build_user_prompt",
    "extract_delta_from_chunk",
    "parse_sse_data_payload",
    "trim_to_context",
]
