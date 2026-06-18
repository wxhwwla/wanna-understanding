# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""DeepSeek API 客户端与结构化输出解析。"""

from __future__ import annotations

import hashlib
import re
import time
from collections.abc import Callable
from typing import Any

import httpx
from PIL import Image

from wanna_understanding.config import Settings

from .cache import AnalysisResult
from .prompt import SYSTEM_PROMPT, VISION_SYSTEM_PROMPT, build_user_prompt
from .stream import iter_sse_deltas

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
        """分析代码文本并返回结构化结果（非流式）。"""
        prepared = self._prepare_request(code, code_hash)
        if isinstance(prepared, AnalysisResult):
            return prepared
        digest, _code = prepared
        raw = self._call_api(_code, stream=False)
        return self._build_result(digest, raw)

    def analyze_stream(
        self,
        code: str,
        on_delta: Callable[[str, str], None] | None = None,
        code_hash: str | None = None,
    ) -> AnalysisResult:
        """流式分析代码；on_delta 接收 (增量, 累计全文)。"""
        prepared = self._prepare_request(code, code_hash)
        if isinstance(prepared, AnalysisResult):
            return prepared
        digest, _code = prepared
        parts: list[str] = []

        def _collect(delta: str) -> None:
            parts.append(delta)
            if on_delta is not None:
                on_delta(delta, "".join(parts))

        raw = self._call_api(_code, stream=True, on_sse_delta=_collect)
        return self._build_result(digest, raw)

    def analyze_vision(self, image: Image.Image) -> AnalysisResult:  # type: ignore[name-defined, unused-ignore]
        """分析代码截图（多模态视觉模式，跳过 OCR）。"""
        if not self._settings.has_api_key:
            return AnalysisResult(
                code_hash="",
                summary="未配置 DEEPSEEK_API_KEY",
                bugs=[],
                suggestions=["设置 API Key 后重启程序"],
                raw_response="",
            )
        import base64
        from io import BytesIO

        # 压缩图片：最长边限制 2048px，JPEG 质量 75，减小传输量
        img = image.convert("RGB")
        longest = max(img.width, img.height)
        if longest > 2048:
            scale = 2048 / longest
            img = img.resize((int(img.width * scale), int(img.height * scale)),
                             Image.Resampling.LANCZOS)
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=75)
        image_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        image_data_uri = f"data:image/jpeg;base64,{image_b64}"

        url = f"{self._settings.deepseek_api_base.rstrip('/')}/chat/completions"
        payload: dict[str, Any] = {
            "model": self._settings.deepseek_model,
            "messages": [
                {"role": "system", "content": VISION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "请分析以下代码截图："},
                        {"type": "image_url", "image_url": {"url": image_data_uri}},
                    ],
                },
            ],
            "temperature": 0.2,
            "max_tokens": 2048,
        }
        headers = {
            "Authorization": f"Bearer {self._settings.deepseek_api_key}",
            "Content-Type": "application/json",
        }
        try:
            # vision 调用单独用长超时（最大 300s）
            vision_timeout = httpx.Timeout(
                connect=min(60.0, self._settings.request_timeout),
                read=min(300.0, max(self._settings.request_timeout, 120.0)),
                write=60.0,
                pool=60.0,
            )
            response = httpx.post(url, json=payload, headers=headers,
                                  timeout=vision_timeout)
            response.raise_for_status()
            data = response.json()
            raw = str(data["choices"][0]["message"]["content"])
            return self._build_result("vision", raw)
        except httpx.TimeoutException:
            return AnalysisResult(
                code_hash="",
                summary="分析失败：AI API 连接超时，请检查网络或增大超时设置",
                bugs=[],
                suggestions=["检查网络连接", "增大 request_timeout 设置"],
                raw_response="",
            )
        except httpx.HTTPStatusError as exc:
            detail = str(exc)
            # 尝试获取 API 返回的实际错误消息
            try:
                body = exc.response.json()
                api_msg = body.get("error", {}).get("message", str(body))
                detail = f"{detail}\nAPI 返回: {api_msg}"
            except Exception:
                detail = f"{detail}\n响应体: {exc.response.text[:300]}"
            if exc.response.status_code == 401:
                detail = "API Key 无效或未配置"
            return AnalysisResult(
                code_hash="",
                summary=f"分析失败：{detail}",
                bugs=[],
                suggestions=[
                    "确认使用的 AI 模型是否支持 vision（多模态）",
                    "尝试换用支持 vision 的模型，如 deepseek-vision",
                    "或在 .env 中设置 WU_USE_VISION=false 回退 OCR 模式",
                ],
                raw_response=str(exc),
            )

    def _prepare_request(
        self,
        code: str,
        code_hash: str | None,
    ) -> AnalysisResult | tuple[str, str]:
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
        return digest, code

    def _build_result(self, code_hash: str, raw: str) -> AnalysisResult:
        parsed = self._parse_response(raw)
        return AnalysisResult(
            code_hash=code_hash,
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

    def _call_api(
        self,
        code: str,
        *,
        stream: bool,
        on_sse_delta: Callable[[str], None] | None = None,
    ) -> str:
        url = f"{self._settings.deepseek_api_base.rstrip('/')}/chat/completions"
        payload: dict[str, Any] = {
            "model": self._settings.deepseek_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(code)},
            ],
            "temperature": 0.2,
            "stream": stream,
        }
        headers = {
            "Authorization": f"Bearer {self._settings.deepseek_api_key}",
            "Content-Type": "application/json",
        }
        if not stream:
            response = self._get_client().post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return str(data["choices"][0]["message"]["content"])

        parts: list[str] = []
        with self._get_client().stream(
            "POST", url, json=payload, headers=headers
        ) as response:
            response.raise_for_status()
            for delta in iter_sse_deltas(response.iter_lines()):
                parts.append(delta)
                if on_sse_delta is not None:
                    on_sse_delta(delta)
        return "".join(parts)

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
