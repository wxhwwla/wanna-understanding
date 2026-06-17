# SPDX-License-Identifier: AGPL-3.0

"""全局配置：API Key、轮询频率、防抖与缓存参数。"""

from __future__ import annotations

import os
import sys
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


def dotenv_path() -> Path:
    """默认 `.env` 路径（当前工作目录）。"""
    return Path(".env")


def get_data_dir() -> Path:
    """用户数据目录（历史记录等）。"""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path.home() / ".local" / "share"
    path = base / "WannaUnderstanding"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _format_env_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


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
    stream_output: bool = True
    stream_ui_interval: float = Field(default=0.1, ge=0.05, le=1.0)
    editor_profile: str = "auto"
    monitor_mode: str = "window"
    monitor_rect: str = ""
    use_uia: bool = False
    overlay_width: int = Field(default=400, ge=200, le=1200)
    overlay_height: int = Field(default=300, ge=150, le=900)
    overlay_opacity: float = Field(default=0.85, gt=0.1, le=1.0)
    request_timeout: float = Field(default=60.0, ge=5.0, le=300.0)
    history_enabled: bool = True
    history_max_entries: int = Field(default=50, ge=1, le=500)
    tray_enabled: bool = True

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
            stream_output=cls._parse_bool(os.getenv("WU_STREAM_OUTPUT", "true")),
            stream_ui_interval=float(os.getenv("WU_STREAM_UI_INTERVAL", "0.1")),
            editor_profile=os.getenv("WU_EDITOR_PROFILE", "auto"),
            monitor_mode=os.getenv("WU_MONITOR_MODE", "window"),
            monitor_rect=os.getenv("WU_MONITOR_RECT", ""),
            use_uia=cls._parse_bool(os.getenv("WU_USE_UIA", "false")),
            overlay_width=int(os.getenv("WU_OVERLAY_WIDTH", "400")),
            overlay_height=int(os.getenv("WU_OVERLAY_HEIGHT", "300")),
            overlay_opacity=float(os.getenv("WU_OVERLAY_OPACITY", "0.85")),
            request_timeout=float(os.getenv("WU_REQUEST_TIMEOUT", "60.0")),
            history_enabled=cls._parse_bool(os.getenv("WU_HISTORY_ENABLED", "true")),
            history_max_entries=int(os.getenv("WU_HISTORY_MAX_ENTRIES", "50")),
            tray_enabled=cls._parse_bool(os.getenv("WU_TRAY_ENABLED", "true")),
        )


def _settings_env_map(settings: Settings) -> dict[str, str]:
    """将 Settings 映射为环境变量键值。"""
    return {
        "DEEPSEEK_API_KEY": settings.deepseek_api_key,
        "WU_POLL_INTERVAL": _format_env_value(settings.poll_interval),
        "WU_DEBOUNCE_DELAY": _format_env_value(settings.debounce_delay),
        "WU_CONTEXT_MAX_LINES": _format_env_value(settings.context_max_lines),
        "WU_STREAM_OUTPUT": _format_env_value(settings.stream_output),
        "WU_EDITOR_PROFILE": settings.editor_profile,
        "WU_MONITOR_MODE": settings.monitor_mode,
        "WU_MONITOR_RECT": settings.monitor_rect,
        "WU_USE_UIA": _format_env_value(settings.use_uia),
        "WU_HISTORY_ENABLED": _format_env_value(settings.history_enabled),
        "WU_HISTORY_MAX_ENTRIES": _format_env_value(settings.history_max_entries),
        "WU_TRAY_ENABLED": _format_env_value(settings.tray_enabled),
        "WU_OVERLAY_WIDTH": _format_env_value(settings.overlay_width),
        "WU_OVERLAY_HEIGHT": _format_env_value(settings.overlay_height),
        "WU_OVERLAY_OPACITY": _format_env_value(settings.overlay_opacity),
    }


def save_settings_to_dotenv(
    settings: Settings,
    path: Path | None = None,
) -> Path:
    """将可编辑配置写入 `.env`（保留未管理键与注释）。"""
    target = path or dotenv_path()
    managed = _settings_env_map(settings)
    lines_out: list[str] = []
    seen: set[str] = set()
    if target.is_file():
        for raw_line in target.read_text(encoding="utf-8").splitlines():
            stripped = raw_line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key = stripped.split("=", 1)[0].strip()
                if key in managed:
                    lines_out.append(f"{key}={managed.pop(key)}")
                    seen.add(key)
                    continue
            lines_out.append(raw_line)
    for key, value in managed.items():
        if key not in seen:
            lines_out.append(f"{key}={value}")
    target.write_text("\n".join(lines_out).rstrip() + "\n", encoding="utf-8")
    return target


def load_settings() -> Settings:
    """加载全局配置。"""
    return Settings.from_env()
