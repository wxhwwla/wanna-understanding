# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""运行时设置对话框。"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox

from wanna_understanding.config import (
    DEEPSEEK_MODEL_PRESETS,
    Settings,
    save_settings_to_dotenv,
)
from wanna_understanding.screen.custom_region import format_monitor_rect
from wanna_understanding.screen.region_picker import pick_screen_region

# 字体常量
_FONT_HINT = ("Microsoft YaHei UI", 10)


class SettingsDialog:
    """编辑常用配置并保存到 `.env`。"""

    _EDITOR_OPTIONS = (
        "auto",
        "vscode_dark",
        "vscode_light",
        "cursor_dark",
        "trae_dark",
        "pycharm_dark",
        "pycharm_light",
        "generic",
    )
    _MONITOR_OPTIONS = ("window", "custom")

    def __init__(
        self,
        parent: tk.Misc,
        settings: Settings,
        on_saved: Callable[[Settings], None] | None = None,
    ) -> None:
        self._original = settings
        self._on_saved = on_saved
        self._window = tk.Toplevel(parent)
        self._window.title("设置")
        self._window.geometry("480x760")
        self._window.configure(bg="#1e1e1e")
        self._window.transient(parent)
        self._window.grab_set()

        # 统一设置默认字体 (Tk option database)
        # 注意：含空格的字体名必须用花括号括起来
        self._window.option_add("*Font", "{Microsoft YaHei UI} 12")
        self._window.option_add("*Entry.Font", "Consolas 12")
        self._window.option_add("*Button.Font", "{Microsoft YaHei UI} 12")
        self._window.option_add("*Menu.Font", "{Microsoft YaHei UI} 12")
        self._window.option_add("*Checkbutton.Font", "{Microsoft YaHei UI} 12")

        form = tk.Frame(self._window, bg="#1e1e1e", padx=12, pady=12)
        form.pack(fill="both", expand=True)

        row = 0
        self._api_key = self._add_entry(
            form, row, "DeepSeek API Key", settings.deepseek_api_key
        )
        row += 1
        preset_value = (
            settings.deepseek_model
            if settings.deepseek_model in DEEPSEEK_MODEL_PRESETS
            else "custom"
        )
        self._model_preset = self._add_option(
            form,
            row,
            "AI 模型",
            (*DEEPSEEK_MODEL_PRESETS, "custom"),
            preset_value,
        )
        row += 1
        custom_default = (
            settings.deepseek_model
            if settings.deepseek_model not in DEEPSEEK_MODEL_PRESETS
            else ""
        )
        self._model_custom = self._add_entry(
            form, row, "自定义模型 ID", custom_default
        )
        row += 1
        tk.Label(
            form,
            text="Flash 更快更省；Pro 更强。同一 API Key，仅 model 参数不同。",
            bg="#1e1e1e",
            fg="#888888",
            font=_FONT_HINT,
            anchor="w",
            wraplength=420,
            justify="left",
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 4))
        row += 1
        self._poll = self._add_entry(
            form, row, "轮询间隔 (秒)", str(settings.poll_interval)
        )
        row += 1
        self._debounce = self._add_entry(
            form, row, "防抖延迟 (秒)", str(settings.debounce_delay)
        )
        row += 1
        self._context_lines = self._add_entry(
            form, row, "最大发送行数", str(settings.context_max_lines)
        )
        row += 1
        self._overlay_width = self._add_entry(
            form, row, "悬浮窗宽度", str(settings.overlay_width)
        )
        row += 1
        self._overlay_height = self._add_entry(
            form, row, "悬浮窗高度", str(settings.overlay_height)
        )
        row += 1
        self._overlay_opacity = self._add_entry(
            form, row, "悬浮窗透明度 (0-1)", str(settings.overlay_opacity)
        )
        row += 1
        self._stream = self._add_bool(form, row, "流式 AI 输出", settings.stream_output)
        row += 1
        self._use_uia = self._add_bool(
            form, row, "UI Automation 优先", settings.use_uia
        )
        row += 1
        tk.Label(
            form,
            text="UIA 对 VS Code/Cursor 等 Electron 编辑器通常无效，建议保持关闭。",
            bg="#1e1e1e",
            fg="#888888",
            font=_FONT_HINT,
            anchor="w",
            wraplength=420,
            justify="left",
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 4))
        row += 1
        self._history = self._add_bool(
            form, row, "保存分析历史", settings.history_enabled
        )
        row += 1
        self._tray = self._add_bool(form, row, "系统托盘图标", settings.tray_enabled)
        row += 1
        self._editor = self._add_option(
            form,
            row,
            "编辑器配置",
            self._EDITOR_OPTIONS,
            settings.editor_profile,
        )
        row += 1
        self._monitor_mode = self._add_option(
            form,
            row,
            "监控模式",
            self._MONITOR_OPTIONS,
            settings.monitor_mode,
        )
        row += 1
        self._monitor_rect = self._add_entry(
            form, row, "自定义区域 (L,T,W,H)", settings.monitor_rect
        )
        row += 1
        pick_row = tk.Frame(form, bg="#1e1e1e")
        pick_row.grid(row=row, column=0, columnspan=2, sticky="ew", pady=4)
        tk.Button(pick_row, text="框选监控区域…", command=self._on_pick_region).pack(
            side="left"
        )
        row += 1

        hint = tk.Label(
            form,
            text="保存后写入 .env；保存后立即生效。",
            bg="#1e1e1e",
            fg="#888888",
            font=_FONT_HINT,
            anchor="w",
            wraplength=420,
            justify="left",
        )
        hint.grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 0))

        btn_row = tk.Frame(self._window, bg="#1e1e1e", padx=12, pady=8)
        btn_row.pack(fill="x")
        tk.Button(btn_row, text="保存", command=self._on_save).pack(side="right")
        tk.Button(btn_row, text="取消", command=self._window.destroy).pack(
            side="right", padx=8
        )

    def _on_pick_region(self) -> None:
        self._window.grab_release()
        rect = pick_screen_region(self._window)
        self._window.grab_set()
        if rect is None:
            return
        self._monitor_mode.set("custom")
        self._monitor_rect.delete(0, tk.END)
        self._monitor_rect.insert(0, format_monitor_rect(rect))

    def _add_entry(
        self,
        parent: tk.Frame,
        row: int,
        label: str,
        value: str,
    ) -> tk.Entry:
        tk.Label(parent, text=label, bg="#1e1e1e", fg="#cccccc", anchor="w").grid(
            row=row, column=0, sticky="w", pady=4
        )
        entry = tk.Entry(parent, bg="#2d2d2d", fg="#d4d4d4", insertbackground="#d4d4d4")
        entry.insert(0, value)
        entry.grid(row=row, column=1, sticky="ew", pady=4)
        parent.grid_columnconfigure(1, weight=1)
        return entry

    def _add_bool(
        self,
        parent: tk.Frame,
        row: int,
        label: str,
        value: bool,
    ) -> tk.BooleanVar:
        var = tk.BooleanVar(value=value)
        tk.Checkbutton(
            parent,
            text=label,
            variable=var,
            bg="#1e1e1e",
            fg="#cccccc",
            selectcolor="#2d2d2d",
            activebackground="#1e1e1e",
            anchor="w",
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=4)
        return var

    def _add_option(
        self,
        parent: tk.Frame,
        row: int,
        label: str,
        options: tuple[str, ...],
        value: str,
    ) -> tk.StringVar:
        tk.Label(parent, text=label, bg="#1e1e1e", fg="#cccccc", anchor="w").grid(
            row=row, column=0, sticky="w", pady=4
        )
        var = tk.StringVar(value=value if value in options else options[0])
        menu = tk.OptionMenu(parent, var, *options)
        menu.configure(bg="#2d2d2d", fg="#d4d4d4", highlightthickness=0)
        menu["menu"].configure(bg="#2d2d2d", fg="#d4d4d4")
        menu.grid(row=row, column=1, sticky="ew", pady=4)
        return var

    def _resolve_model_id(self) -> str:
        preset = self._model_preset.get().strip()
        if preset != "custom":
            return preset
        return self._model_custom.get().strip()

    def _on_save(self) -> None:
        model_id = self._resolve_model_id()
        if not model_id:
            messagebox.showerror(
                "输入错误",
                "请选择 AI 模型，或填写自定义模型 ID。",
                parent=self._window,
            )
            return
        try:
            updated = self._original.model_copy(
                update={
                    "deepseek_api_key": self._api_key.get().strip(),
                    "deepseek_model": model_id,
                    "poll_interval": float(self._poll.get().strip()),
                    "debounce_delay": float(self._debounce.get().strip()),
                    "context_max_lines": int(self._context_lines.get().strip()),
                    "overlay_width": int(self._overlay_width.get().strip()),
                    "overlay_height": int(self._overlay_height.get().strip()),
                    "overlay_opacity": float(self._overlay_opacity.get().strip()),
                    "stream_output": self._stream.get(),
                    "use_uia": self._use_uia.get(),
                    "history_enabled": self._history.get(),
                    "tray_enabled": self._tray.get(),
                    "editor_profile": self._editor.get(),
                    "monitor_mode": self._monitor_mode.get(),
                    "monitor_rect": self._monitor_rect.get().strip(),
                }
            )
        except ValueError as exc:
            messagebox.showerror(
                "输入错误",
                f"请检查数值字段：{exc}",
                parent=self._window,
            )
            return
        try:
            save_settings_to_dotenv(updated)
        except OSError as exc:
            messagebox.showerror("保存失败", str(exc), parent=self._window)
            return
        if self._on_saved is not None:
            self._on_saved(updated)
        messagebox.showinfo("已保存", "设置已写入 .env", parent=self._window)
        self._window.destroy()
