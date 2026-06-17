# SPDX-License-Identifier: AGPL-3.0

"""apply_geometry 单元测试（不启动 GUI 主循环）。"""

from unittest.mock import MagicMock

from wanna_understanding.ui.overlay import OverlayWindow


def test_apply_geometry_updates_size_and_opacity(monkeypatch) -> None:
    monkeypatch.setattr(OverlayWindow, "__init__", lambda self, *a, **k: None)
    overlay = OverlayWindow.__new__(OverlayWindow)
    overlay.width = 400
    overlay.height = 300
    overlay.opacity = 0.85
    overlay.root = MagicMock()
    overlay.root.winfo_x.return_value = 10
    overlay.root.winfo_y.return_value = 20

    overlay.apply_geometry(500, 350, 0.9)

    assert overlay.width == 500
    assert overlay.height == 350
    assert overlay.opacity == 0.9
    overlay.root.attributes.assert_called_with("-alpha", 0.9)
    overlay.root.geometry.assert_called_with("500x350+10+20")
