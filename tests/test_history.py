# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""分析历史存储测试。"""

from pathlib import Path

from wanna_understanding.ai.cache import AnalysisResult
from wanna_understanding.ai.history import HistoryStore


def _sample_result(code_hash: str = "abc") -> AnalysisResult:
    return AnalysisResult(
        code_hash=code_hash,
        summary="示例功能",
        bugs=["可能空指针"],
        suggestions=["加类型注解"],
    )


def test_history_append_and_persist(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    store = HistoryStore(path, max_entries=10)
    store.append(
        window_title="app.py - Cursor",
        code="def main():\n    pass",
        result=_sample_result(),
    )
    reloaded = HistoryStore(path, max_entries=10)
    entries = reloaded.list_entries()
    assert len(entries) == 1
    assert entries[0].window_title == "app.py - Cursor"
    assert "def main" in entries[0].code_preview


def test_history_respects_max_entries(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    store = HistoryStore(path, max_entries=2)
    for index in range(3):
        store.append(
            window_title=f"w{index}",
            code=f"code {index}",
            result=_sample_result(f"h{index}"),
        )
    assert len(store.list_entries()) == 2
    assert store.list_entries()[0].window_title == "w2"


def test_history_clear(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    store = HistoryStore(path)
    store.append(window_title="x", code="y", result=_sample_result())
    store.clear()
    assert store.list_entries() == []
