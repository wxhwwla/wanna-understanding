# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""剪贴板读取：通过模拟 Ctrl+A → Ctrl+C 从活动编辑器获取精准代码文本。

工作原理：
1. 保存当前系统剪贴板内容
2. 向活动窗口发送 Ctrl+A（全选）+ Ctrl+C（复制）
3. 读取剪贴板中的代码文本
4. 恢复原剪贴板内容

优势：无需 OCR、无需插件、跨所有编辑器（VS Code / Cursor / Trae / PyCharm / 记事本等）。
"""

from __future__ import annotations

import subprocess
import time

import win32clipboard  # type: ignore[import-untyped]
import win32con  # type: ignore[import-untyped]
import win32gui  # type: ignore[import-untyped]

from wanna_understanding.logger import get_logger

log = get_logger(__name__)

_CLIPBOARD_RETRY = 0.15  # 读剪贴板重试等待


def _send_select_all_copy() -> None:
    """用 PowerShell SendKeys 发送 Ctrl+A → Ctrl+C。

    SendKeys 通过 COM (WScript.Shell) 注入键盘事件，
    走的是不同的系统路径，比 SendInput/keybd_event 更可靠，
    对 Electron 应用（VS Code / Trae / Cursor）实测有效。
    """
    ps_script = (
        '$wshell = New-Object -ComObject wscript.shell;'
        'Start-Sleep -Milliseconds 50;'
        '$wshell.SendKeys("^a");'     # Ctrl+A
        'Start-Sleep -Milliseconds 50;'
        '$wshell.SendKeys("^c");'     # Ctrl+C
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            timeout=10,
        )
        log.debug("剪贴板: PowerShell SendKeys 执行完成")
    except Exception as exc:
        log.warning("剪贴板: PowerShell SendKeys 异常: %s", exc)


def _save_clipboard() -> str | None:
    """保存当前剪贴板文本。"""
    try:
        win32clipboard.OpenClipboard()
        try:
            if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                return str(data) if data else None
        finally:
            win32clipboard.CloseClipboard()
    except Exception:
        pass
    return None


def _restore_clipboard(text: str | None) -> None:
    """恢复剪贴板内容。"""
    if text is None:
        return
    try:
        for _ in range(3):
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
                return
            finally:
                win32clipboard.CloseClipboard()
        log.warning("剪贴板恢复失败（重试 3 次）")
    except Exception as exc:
        log.warning("剪贴板恢复异常: %s", exc)


def read_editor_text(*, hwnd: int | None = None) -> str | None:
    """从活动编辑器通过剪贴板读取代码文本。

    流程：保存剪贴板 → Ctrl+A → Ctrl+C → 读剪贴板 → 恢复剪贴板。

    参数：
        hwnd: 窗口句柄。为 None 时自动使用前台窗口。

    返回：
        编辑器中的文本，失败返回 None。
    """
    # 确保目标窗口在前台
    target = hwnd or win32gui.GetForegroundWindow()
    current_fg = win32gui.GetForegroundWindow()
    log.debug("剪贴板: 目标窗口=%d, 当前前台=%d", target, current_fg)
    if target != current_fg:
        log.debug("剪贴板: 尝试切换前台到 %d", target)
        win32gui.SetForegroundWindow(target)
        time.sleep(0.2)

    # 保存剪贴板
    saved = _save_clipboard()
    log.debug("剪贴板: 已保存原内容, has_data=%s", saved is not None)

    try:
        # 清空剪贴板（确保读到的数据是刚复制的）
        cleared = False
        for i in range(3):
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                cleared = True
                log.debug("剪贴板: 已清空（第 %d 次）", i + 1)
                break
            finally:
                win32clipboard.CloseClipboard()
        if not cleared:
            log.warning("剪贴板: 清空失败（3 次重试）")

        # Ctrl+A → Ctrl+C（用 PowerShell SendKeys，兼容 Electron 应用）
        log.debug("剪贴板: 执行 Ctrl+A → Ctrl+C")
        _send_select_all_copy()
        time.sleep(0.2)

        # 诊断：检查剪贴板当前有哪些格式
        try:
            win32clipboard.OpenClipboard()
            try:
                fmt = 0
                formats: list[str] = []
                while True:
                    fmt = win32clipboard.EnumClipboardFormats(fmt)
                    if fmt == 0:
                        break
                    name = win32clipboard.GetClipboardFormatName(fmt) if fmt >= 0xC000 else hex(fmt)
                    formats.append(str(name))
                if formats:
                    log.debug("剪贴板: 可用格式: %s", ", ".join(formats))
                else:
                    log.debug("剪贴板: 无可用格式（EmptyClipboard 后未写入）")
            finally:
                win32clipboard.CloseClipboard()
        except Exception as exc:
            log.debug("剪贴板: 格式枚举异常: %s", exc)

        # 读取剪贴板（CF_UNICODETEXT + CF_TEXT 双格式兜底）
        text: str | None = None
        for attempt in range(8):
            try:
                win32clipboard.OpenClipboard()
                try:
                    raw: object = None
                    if win32clipboard.IsClipboardFormatAvailable(
                        win32con.CF_UNICODETEXT
                    ):
                        raw = win32clipboard.GetClipboardData(
                            win32con.CF_UNICODETEXT
                        )
                    elif win32clipboard.IsClipboardFormatAvailable(
                        win32con.CF_TEXT
                    ):
                        raw = win32clipboard.GetClipboardData(
                            win32con.CF_TEXT
                        )
                    if raw is not None:
                        text = str(raw) if raw else None
                        if text and text.strip():
                            log.debug("剪贴板: 第 %d 次尝试读取成功 (%d 字符)",
                                      attempt + 1, len(text))
                            break
                finally:
                    win32clipboard.CloseClipboard()
            except Exception as exc:
                log.debug("剪贴板: 第 %d 次尝试异常: %s", attempt + 1, exc)
            time.sleep(_CLIPBOARD_RETRY)

        if text is None:
            log.warning("剪贴板读取失败：未获取到文本（5 次重试后）")
            return None

        # 去尾 + 过滤空白
        text = text.strip()
        if not text:
            log.warning("剪贴板读取失败：内容为空")
            return None

        log.info("剪贴板读取成功: %d 字符", len(text))
        log.debug("前 100 字符: %r", text[:100])
        return text

    finally:
        # 恢复剪贴板
        _restore_clipboard(saved)
