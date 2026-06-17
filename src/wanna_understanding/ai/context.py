# SPDX-License-Identifier: AGPL-3.0

"""代码上下文裁剪：减少发送给 AI 的 token 用量。"""

from __future__ import annotations


def trim_to_context(code: str, max_lines: int = 20) -> str:
    """裁剪为最多 max_lines 行，默认取中间可见区域近似值。

    Args:
        code: OCR 识别出的完整代码文本。
        max_lines: 发送给 AI 的最大行数。

    Returns:
        裁剪后的代码字符串；不足 max_lines 时原样返回。
    """
    if max_lines < 1:
        return ""
    lines = code.splitlines()
    if len(lines) <= max_lines:
        return code
    start = (len(lines) - max_lines) // 2
    return "\n".join(lines[start : start + max_lines])
