# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""分析历史浏览对话框。"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import font as tkfont
from tkinter import messagebox

from wanna_understanding.ai.history import HistoryEntry, HistoryStore


class HistoryDialog:
    """列出历史分析记录并查看详情。"""

    def __init__(
        self,
        parent: tk.Misc,
        store: HistoryStore,
        on_select: Callable[[HistoryEntry], None] | None = None,
    ) -> None:
        self._store = store
        self._on_select = on_select
        self._entries = store.list_entries()
        self._window = tk.Toplevel(parent)
        self._window.title("分析历史")
        self._window.geometry("720x480")
        self._window.configure(bg="#1e1e1e")
        self._window.transient(parent)
        self._window.grab_set()

        body = tk.Frame(self._window, bg="#1e1e1e")
        body.pack(fill="both", expand=True, padx=8, pady=8)

        list_frame = tk.Frame(body, bg="#1e1e1e")
        list_frame.pack(side="left", fill="y")

        self._listbox = tk.Listbox(
            list_frame,
            width=32,
            bg="#2d2d2d",
            fg="#d4d4d4",
            selectbackground="#094771",
            font=tkfont.Font(family="Microsoft YaHei UI", size=12),
            relief="flat",
            borderwidth=0,
        )
        self._listbox.pack(side="left", fill="y", expand=True)
        self._listbox.bind("<<ListboxSelect>>", self._on_list_select)
        self._listbox.bind("<Double-Button-1>", self._on_apply)

        scroll = tk.Scrollbar(list_frame, command=self._listbox.yview)
        scroll.pack(side="right", fill="y")
        self._listbox.configure(yscrollcommand=scroll.set)

        self._detail = tk.Text(
            body,
            wrap="word",
            bg="#2d2d2d",
            fg="#d4d4d4",
            font=tkfont.Font(family="Microsoft YaHei", size=13),
            relief="flat",
            borderwidth=0,
            padx=8,
            pady=8,
        )
        self._detail.pack(side="left", fill="both", expand=True, padx=(8, 0))

        btn_row = tk.Frame(self._window, bg="#1e1e1e")
        btn_row.pack(fill="x", padx=8, pady=(0, 8))
        tk.Button(btn_row, text="应用到悬浮窗", command=self._on_apply).pack(
            side="left"
        )
        tk.Button(btn_row, text="清空历史", command=self._on_clear).pack(
            side="left", padx=8
        )
        tk.Button(btn_row, text="关闭", command=self._window.destroy).pack(
            side="right"
        )

        self._populate()

    def _populate(self) -> None:
        self._listbox.delete(0, "end")
        for entry in self._entries:
            self._listbox.insert("end", entry.label())
        if self._entries:
            self._listbox.selection_set(0)
            self._show_entry(self._entries[0])
        else:
            self._set_detail("暂无分析历史。")

    def _selected_entry(self) -> HistoryEntry | None:
        selection = self._listbox.curselection()
        if not selection:
            return None
        index = selection[0]
        if index < 0 or index >= len(self._entries):
            return None
        return self._entries[index]

    def _on_list_select(self, _event: object = None) -> None:
        entry = self._selected_entry()
        if entry is not None:
            self._show_entry(entry)

    def _show_entry(self, entry: HistoryEntry) -> None:
        lines = [
            f"窗口：{entry.window_title or '未知'}",
            f"时间：{entry.label().split('  ', 1)[0]}",
            "",
            "代码预览：",
            entry.code_preview or "(无)",
            "",
            entry.result.format_display(),
        ]
        self._set_detail("\n".join(lines))

    def _set_detail(self, text: str) -> None:
        self._detail.configure(state="normal")
        self._detail.delete("1.0", "end")
        self._detail.insert("end", text)
        self._detail.configure(state="disabled")

    def _on_apply(self, _event: object = None) -> None:
        entry = self._selected_entry()
        if entry is None:
            return
        if self._on_select is not None:
            self._on_select(entry)
        self._window.destroy()

    def _on_clear(self) -> None:
        if not self._entries:
            return
        if not messagebox.askyesno(
            "确认",
            "确定清空全部历史记录？",
            parent=self._window,
        ):
            return
        self._store.clear()
        self._entries = []
        self._populate()
