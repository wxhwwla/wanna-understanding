# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""系统托盘图标与右键菜单。"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw

if TYPE_CHECKING:
    import pystray


def create_tray_image(size: int = 64) -> Image.Image:
    """生成托盘图标（无需外部资源文件）。"""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    margin = max(4, size // 8)
    draw.ellipse(
        (margin, margin, size - margin, size - margin),
        fill="#4fc3f7",
        outline="#0288d1",
        width=max(1, size // 32),
    )
    inner = size // 3
    draw.ellipse(
        (inner, inner, size - inner, size - inner),
        fill="#e1f5fe",
    )
    pupil = size // 2
    radius = max(2, size // 10)
    draw.ellipse(
        (pupil - radius, pupil - radius, pupil + radius, pupil + radius),
        fill="#01579b",
    )
    return image


class TrayController:
    """后台托盘：菜单操作通过 schedule 回调到 Tk 主线程。"""

    def __init__(
        self,
        *,
        on_toggle: Callable[[], None],
        on_freeze: Callable[[], None],
        on_history: Callable[[], None],
        on_settings: Callable[[], None],
        on_quit: Callable[[], None],
        schedule: Callable[[Callable[[], None]], None],
        tooltip: str = "Wanna Understanding",
    ) -> None:
        self._on_toggle = on_toggle
        self._on_freeze = on_freeze
        self._on_history = on_history
        self._on_settings = on_settings
        self._on_quit = on_quit
        self._schedule = schedule
        self._tooltip = tooltip
        self._icon: pystray.Icon | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """在后台线程启动托盘图标。"""
        if self._icon is not None:
            return
        import pystray

        menu = pystray.Menu(
            pystray.MenuItem("显示/隐藏悬浮窗", self._menu_toggle, default=True),
            pystray.MenuItem("冻结/解冻内容", self._menu_freeze),
            pystray.MenuItem("分析历史", self._menu_history),
            pystray.MenuItem("设置", self._menu_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._menu_quit),
        )
        self._icon = pystray.Icon(
            "wanna_understanding",
            create_tray_image(),
            self._tooltip,
            menu,
        )
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """移除托盘图标。"""
        if self._icon is None:
            return
        self._icon.stop()
        self._icon = None
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _menu_toggle(self, _icon: object, _item: object) -> None:
        self._schedule(self._on_toggle)

    def _menu_freeze(self, _icon: object, _item: object) -> None:
        self._schedule(self._on_freeze)

    def _menu_history(self, _icon: object, _item: object) -> None:
        self._schedule(self._on_history)

    def _menu_settings(self, _icon: object, _item: object) -> None:
        self._schedule(self._on_settings)

    def _menu_quit(self, _icon: object, _item: object) -> None:
        self._schedule(self._on_quit)
