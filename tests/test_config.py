# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""配置加载测试。"""

from wanna_understanding.config import (
    Settings,
    load_settings,
    save_settings_to_dotenv,
)


def test_settings_reads_env(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    settings = Settings.from_env()
    assert settings.deepseek_api_key == "test-key"
    assert settings.has_api_key is True


def test_load_settings_returns_defaults() -> None:
    settings = load_settings()
    assert settings.poll_interval == 2.0
    assert settings.debounce_delay == 0.5
    assert settings.monitor_mode == "window"
    assert settings.use_uia is False


def test_monitor_env_vars(monkeypatch) -> None:
    monkeypatch.setenv("WU_MONITOR_MODE", "custom")
    monkeypatch.setenv("WU_MONITOR_RECT", "10,20,300,400")
    monkeypatch.setenv("WU_USE_UIA", "true")
    settings = Settings.from_env()
    assert settings.monitor_mode == "custom"
    assert settings.monitor_rect == "10,20,300,400"
    assert settings.use_uia is True


def test_save_settings_to_dotenv_roundtrip(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DEEPSEEK_API_KEY=old\n# comment\nWU_POLL_INTERVAL=9\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    settings = Settings(
        deepseek_api_key="new-key",
        deepseek_model="deepseek-v4-pro",
        poll_interval=2.5,
        debounce_delay=0.6,
        context_max_lines=30,
        stream_output=False,
        editor_profile="pycharm_dark",
        monitor_mode="custom",
        monitor_rect="1,2,3,4",
        use_uia=True,
        history_enabled=False,
        history_max_entries=25,
        tray_enabled=False,
        overlay_width=450,
        overlay_height=320,
        overlay_opacity=0.9,
    )
    save_settings_to_dotenv(settings)
    text = env_file.read_text(encoding="utf-8")
    assert "DEEPSEEK_API_KEY=new-key" in text
    assert "DEEPSEEK_MODEL=deepseek-v4-pro" in text
    assert "WU_POLL_INTERVAL=2.5" in text
    assert "# comment" in text
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    for key in (
        "WU_POLL_INTERVAL",
        "WU_DEBOUNCE_DELAY",
        "WU_CONTEXT_MAX_LINES",
        "WU_STREAM_OUTPUT",
        "WU_EDITOR_PROFILE",
        "WU_MONITOR_MODE",
        "WU_MONITOR_RECT",
        "WU_USE_UIA",
        "WU_HISTORY_ENABLED",
        "WU_HISTORY_MAX_ENTRIES",
        "WU_TRAY_ENABLED",
        "WU_OVERLAY_WIDTH",
        "WU_OVERLAY_HEIGHT",
        "WU_OVERLAY_OPACITY",
    ):
        monkeypatch.delenv(key, raising=False)
    reloaded = Settings.from_env()
    assert reloaded.deepseek_api_key == "new-key"
    assert reloaded.deepseek_model == "deepseek-v4-pro"
    assert reloaded.poll_interval == 2.5
    assert reloaded.history_enabled is False
    assert reloaded.tray_enabled is False
    assert reloaded.overlay_width == 450
    assert reloaded.overlay_opacity == 0.9
