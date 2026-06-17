# SPDX-License-Identifier: AGPL-3.0

"""全局配置：API Key、轮询频率、防抖与缓存参数。"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


def _load_dotenv(path: Path = Path(".env")) -> None:
    """从 `.env` 加载环境变量（不覆盖已有值）。"""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


class Settings(BaseModel):
    """运行时配置。"""

    deepseek_api_key: str = ""
    deepseek_api_base: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    poll_interval: float = Field(default=2.0, ge=0.5, le=30.0)
    debounce_delay: float = Field(default=0.5, ge=0.1, le=5.0)
    crop_ratio: float = Field(default=0.7, gt=0.0, le=1.0)
    cache_max_size: int = Field(default=100, ge=1, le=1000)
    context_max_lines: int = Field(default=20, ge=5, le=200)
    auto_dark_theme: bool = True
    dark_theme: bool = False
    hotkey_toggle: bool = True
    overlay_width: int = Field(default=400, ge=200, le=1200)
    overlay_height: int = Field(default=300, ge=150, le=900)
    overlay_opacity: float = Field(default=0.85, gt=0.1, le=1.0)
    request_timeout: float = Field(default=60.0, ge=5.0, le=300.0)

    @field_validator("dark_theme", mode="before")
    @classmethod
    def _parse_bool(cls, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @property
    def has_api_key(self) -> bool:
        """是否已配置 AI API Key。"""
        return bool(self.deepseek_api_key.strip())

    @classmethod
    def from_env(cls) -> Settings:
        """从环境变量加载配置。"""
        _load_dotenv()
        return cls(
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            deepseek_api_base=os.getenv(
                "DEEPSEEK_API_BASE", "https://api.deepseek.com"
            ),
            deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            poll_interval=float(os.getenv("WU_POLL_INTERVAL", "2.0")),
            debounce_delay=float(os.getenv("WU_DEBOUNCE_DELAY", "0.5")),
            crop_ratio=float(os.getenv("WU_CROP_RATIO", "0.7")),
            cache_max_size=int(os.getenv("WU_CACHE_MAX_SIZE", "100")),
            context_max_lines=int(os.getenv("WU_CONTEXT_MAX_LINES", "20")),
            auto_dark_theme=cls._parse_bool(os.getenv("WU_AUTO_DARK_THEME", "true")),
            dark_theme=cls._parse_bool(os.getenv("WU_DARK_THEME", "false")),
            hotkey_toggle=cls._parse_bool(os.getenv("WU_HOTKEY_TOGGLE", "true")),
            overlay_width=int(os.getenv("WU_OVERLAY_WIDTH", "400")),
            overlay_height=int(os.getenv("WU_OVERLAY_HEIGHT", "300")),
            overlay_opacity=float(os.getenv("WU_OVERLAY_OPACITY", "0.85")),
            request_timeout=float(os.getenv("WU_REQUEST_TIMEOUT", "60.0")),
        )


def load_settings() -> Settings:
    """加载全局配置。"""
    return Settings.from_env()
