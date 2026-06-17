# SPDX-License-Identifier: AGPL-3.0

"""配置加载测试。"""

from wanna_understanding.config import Settings, load_settings


def test_settings_reads_env(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    settings = Settings.from_env()
    assert settings.deepseek_api_key == "test-key"
    assert settings.has_api_key is True


def test_load_settings_returns_defaults() -> None:
    settings = load_settings()
    assert settings.poll_interval == 2.0
    assert settings.debounce_delay == 0.5
