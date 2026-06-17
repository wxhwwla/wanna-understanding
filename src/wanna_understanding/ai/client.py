# SPDX-License-Identifier: AGPL-3.0

"""DeepSeek API 客户端与结构化输出解析。"""

from __future__ import annotations

import hashlib
import re
import time
from typing import Any

import httpx

from wanna_understanding.config import Settings

from .cache import AnalysisResult
from .prompt import SYSTEM_PROMPT, build_user_prompt

_SECTION_PATTERNS: tuple[tuple[str, str], ...] = (
    ("summary", r"功能说明[:：]\s*(.+?)(?=\n潜在\s*Bug[:：]|\n改进建议[:：]|$)"),
    ("bugs", r"潜在\s*Bug[:：]\s*(.+?)(?=\n改进建议[:：]|$)"),
    ("suggestions", r"改进建议[:：]\s*(.+)$"),
)


class AIClient:
    """调用 DeepSeek 兼容 API 并解析结构化回复。"""

    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self._settings = settings
        self._client = client

    def analyze(self, code: str, code_hash: str | None = None) -> AnalysisResult:
        """分析代码文本并返回结构化结果。"""
        if not code.strip():
            return AnalysisResult(
                code_hash=code_hash or "",
                summary="未识别到有效代码文本",
                bugs=[],
                suggestions=[],
                raw_response="",
            )
        digest = code_hash or hashlib.sha256(code.encode("utf-8")).hexdigest()
        if not self._settings.has_api_key:
            return AnalysisResult(
                code_hash=digest,
                summary="未配置 DEEPSEEK_API_KEY，请在环境变量或 .env 中设置",
                bugs=[],
                suggestions=["设置 API Key 后重启程序"],
                raw_response="",
            )
        raw = self._call_api(code)
        parsed = self._parse_response(raw)
        return AnalysisResult(
            code_hash=digest,
            summary=parsed["summary"],
            bugs=parsed["bugs"],
            suggestions=parsed["suggestions"],
            raw_response=raw,
            timestamp=time.time(),
        )

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self._settings.request_timeout)
        return self._client

    def _call_api(self, code: str) -> str:
        url = f"{self._settings.deepseek_api_base.rstrip('/')}/chat/completions"
        payload: dict[str, Any] = {
            "model": self._settings.deepseek_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(code)},
            ],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self._settings.deepseek_api_key}",
            "Content-Type": "application/json",
        }
        response = self._get_client().post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return str(data["choices"][0]["message"]["content"])

    def _parse_response(self, raw: str) -> dict[str, Any]:
        summary = "无法确定"
        bugs: list[str] = []
        suggestions: list[str] = []
        for name, pattern in _SECTION_PATTERNS:
            match = re.search(pattern, raw, flags=re.IGNORECASE | re.DOTALL)
            if not match:
                continue
            value = match.group(1).strip()
            if name == "summary":
                summary = value.splitlines()[0].strip() or summary
            elif name == "bugs":
                bugs = self._split_items(value)
            elif name == "suggestions":
                suggestions = self._split_items(value)
        if summary == "无法确定" and raw.strip():
            summary = raw.strip().splitlines()[0][:200]
        return {"summary": summary, "bugs": bugs, "suggestions": suggestions}

    @staticmethod
    def _split_items(text: str) -> list[str]:
        normalized = text.strip()
        if not normalized:
            return []
        if normalized in {"暂无", "未发现明显 bug", "无", "None"}:
            return []
        items: list[str] = []
        for line in normalized.splitlines():
            cleaned = re.sub(r"^[\s•\-*\d.)、]+", "", line).strip()
            if cleaned and cleaned not in {"暂无", "未发现明显 bug", "无"}:
                items.append(cleaned)
        return items or [normalized]

    def close(self) -> None:
        """关闭底层 HTTP 客户端。"""
        if self._client is not None:
            self._client.close()
            self._client = None
