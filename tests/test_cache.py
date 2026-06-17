# SPDX-License-Identifier: AGPL-3.0

"""ResultCache 单元测试。"""

from wanna_understanding.ai.cache import AnalysisResult, ResultCache


def _result(code_hash: str) -> AnalysisResult:
    return AnalysisResult(code_hash=code_hash, summary=f"summary-{code_hash}")


def test_cache_hit_moves_entry_to_end() -> None:
    cache = ResultCache(max_size=2)
    cache.put("a", _result("a"))
    cache.put("b", _result("b"))
    assert cache.get("a") is not None
    cache.put("c", _result("c"))
    assert cache.get("b") is None
    assert cache.get("a") is not None


def test_cache_clear() -> None:
    cache = ResultCache()
    cache.put("x", _result("x"))
    cache.clear()
    assert len(cache) == 0
