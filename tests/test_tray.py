# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""系统托盘测试。"""

from unittest.mock import MagicMock

from wanna_understanding.ui.tray import TrayController, create_tray_image


def test_create_tray_image_size() -> None:
    image = create_tray_image(32)
    assert image.size == (32, 32)
    assert image.mode == "RGBA"


def test_tray_controller_start_stop(monkeypatch) -> None:
    fake_icon = MagicMock()
    fake_module = MagicMock()
    fake_module.Icon.return_value = fake_icon
    fake_module.Menu = MagicMock()
    fake_module.MenuItem = MagicMock()
    fake_module.SEPARATOR = object()
    monkeypatch.setitem(__import__("sys").modules, "pystray", fake_module)

    schedule = MagicMock()
    tray = TrayController(
        on_toggle=MagicMock(),
        on_freeze=MagicMock(),
        on_history=MagicMock(),
        on_settings=MagicMock(),
        on_quit=MagicMock(),
        schedule=schedule,
    )
    tray.start()
    fake_module.Icon.assert_called_once()
    fake_icon.run.assert_called_once()
    tray.stop()
    fake_icon.stop.assert_called_once()
