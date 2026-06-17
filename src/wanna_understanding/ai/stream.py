# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""OpenAI 兼容 SSE 流式响应解析。"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any


def extract_delta_from_chunk(chunk: dict[str, Any]) -> str:
    """从 chat.completion chunk 提取文本增量。"""
    choices = chunk.get("choices")
    if not choices:
        return ""
    delta = choices[0].get("delta") or {}
    content = delta.get("content")
    return str(content) if content else ""


def parse_sse_data_payload(payload: str) -> tuple[bool, str]:
    """解析单行 SSE data 负载。

    Returns:
        (is_done, text_delta)。is_done 为 True 表示流结束。
    """
    data = payload.strip()
    if not data:
        return False, ""
    if data == "[DONE]":
        return True, ""
    chunk = json.loads(data)
    return False, extract_delta_from_chunk(chunk)


def _line_to_text(raw: bytes | str) -> str:
    """兼容 httpx 不同版本：iter_lines 可能返回 bytes 或 str。"""
    if isinstance(raw, str):
        return raw.strip()
    return raw.decode("utf-8").strip()


def iter_sse_deltas(lines: Iterator[bytes | str]) -> Iterator[str]:
    """从 httpx 流式响应行迭代文本增量。"""
    for raw in lines:
        line = _line_to_text(raw)
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        done, delta = parse_sse_data_payload(payload)
        if done:
            break
        if delta:
            yield delta
