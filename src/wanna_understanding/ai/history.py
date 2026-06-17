# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""分析历史持久化存储。"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from pydantic import BaseModel, Field

from .cache import AnalysisResult


class HistoryEntry(BaseModel):
    """单条分析历史记录。"""

    entry_id: str
    window_title: str = ""
    code_preview: str = ""
    result: AnalysisResult
    timestamp: float = Field(default_factory=time.time)

    def label(self) -> str:
        """列表展示用短标签。"""
        when = time.strftime("%H:%M:%S", time.localtime(self.timestamp))
        title = self.window_title.strip() or "未知窗口"
        if len(title) > 36:
            title = f"{title[:33]}..."
        return f"{when}  {title}"


class HistoryStore:
    """将分析结果追加写入 JSON 文件。"""

    def __init__(self, path: Path, max_entries: int = 50) -> None:
        self._path = path
        self._max_entries = max(1, max_entries)
        self._entries: list[HistoryEntry] = []
        self._load()

    def set_max_entries(self, max_entries: int) -> None:
        """更新容量上限并裁剪已有记录。"""
        self._max_entries = max(1, max_entries)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries :]
            self._save()

    @property
    def path(self) -> Path:
        """历史文件路径。"""
        return self._path

    def list_entries(self) -> list[HistoryEntry]:
        """按时间倒序返回历史条目。"""
        return list(reversed(self._entries))

    def append(
        self,
        *,
        window_title: str,
        code: str,
        result: AnalysisResult,
    ) -> HistoryEntry:
        """追加一条历史并落盘。"""
        preview = code.strip().replace("\r\n", "\n")
        if len(preview) > 200:
            preview = f"{preview[:197]}..."
        entry = HistoryEntry(
            entry_id=uuid.uuid4().hex,
            window_title=window_title,
            code_preview=preview,
            result=result,
            timestamp=result.timestamp,
        )
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries :]
        self._save()
        return entry

    def clear(self) -> None:
        """清空全部历史。"""
        self._entries.clear()
        self._save()

    def _load(self) -> None:
        if not self._path.is_file():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(raw, list):
            return
        loaded: list[HistoryEntry] = []
        for item in raw:
            try:
                loaded.append(HistoryEntry.model_validate(item))
            except Exception:
                continue
        self._entries = loaded[-self._max_entries :]

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = [entry.model_dump() for entry in self._entries]
        self._path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
