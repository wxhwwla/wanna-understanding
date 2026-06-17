# SPDX-License-Identifier: AGPL-3.0

"""SSE 流式解析测试。"""

import json

from wanna_understanding.ai.stream import (
    extract_delta_from_chunk,
    iter_sse_deltas,
    parse_sse_data_payload,
)


def test_extract_delta_from_chunk() -> None:
    chunk = {"choices": [{"delta": {"content": "hello"}}]}
    assert extract_delta_from_chunk(chunk) == "hello"


def test_parse_sse_done() -> None:
    done, delta = parse_sse_data_payload("[DONE]")
    assert done is True
    assert delta == ""


def test_parse_sse_json_delta() -> None:
    payload = json.dumps({"choices": [{"delta": {"content": "世界"}}]})
    done, delta = parse_sse_data_payload(payload)
    assert done is False
    assert delta == "世界"


def test_iter_sse_deltas_accepts_str_lines() -> None:
    payload = json.dumps({"choices": [{"delta": {"content": "hi"}}]})
    lines = iter(["data: " + payload, "data: [DONE]"])
    assert list(iter_sse_deltas(lines)) == ["hi"]
