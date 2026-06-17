# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""日志系统 — 写入文件，便于诊断运行时问题。

用法：
    from wanna_understanding.logger import setup_logging, get_logger

    setup_logging()          # 程序入口调用一次
    logger = get_logger(__name__)
    logger.info("启动完成")
"""

from __future__ import annotations

import logging
import sys
import threading
import tkinter
from contextlib import suppress
from pathlib import Path

_LOG_FORMAT = "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s"
_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_LOGGER_INITIALIZED = False
_ROOT_LOGGER: logging.Logger | None = None


def setup_logging(
    log_dir: Path | None = None,
    level: int = logging.DEBUG,
    max_bytes: int = 1 * 1024 * 1024,  # 1MB
    backup_count: int = 3,
) -> Path:
    """初始化日志系统，返回日志文件路径。

    Args:
        log_dir: 日志目录。默认 %APPDATA%/WannaUnderstanding/logs/
        level: 日志级别，默认 DEBUG
        max_bytes: 单个日志文件最大字节数，默认 1MB
        backup_count: 保留的旧日志文件数，默认 3

    Returns:
        日志文件路径
    """
    global _LOGGER_INITIALIZED, _ROOT_LOGGER

    from wanna_understanding.config import get_data_dir

    if log_dir is None:
        log_dir = get_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "wanna_understanding.log"

    root = logging.getLogger()
    root.setLevel(level)

    # 移除已有 handler，避免重复
    for handler in list(root.handlers):
        root.removeHandler(handler)

    try:
        from logging.handlers import RotatingFileHandler

        file_handler: logging.Handler = RotatingFileHandler(
            log_file,
            encoding="utf-8",
            maxBytes=max_bytes,
            backupCount=backup_count,
        )
    except ImportError:
        file_handler = logging.FileHandler(
            log_file,
            encoding="utf-8",
            mode="a",
        )

    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, _LOG_DATE_FORMAT))
    root.addHandler(file_handler)

    _ROOT_LOGGER = root
    _LOGGER_INITIALIZED = True

    # 钩住未捕获异常
    _hook_excepthook()
    _hook_tkinter_error()

    root.info("日志系统初始化完成。")
    root.debug("日志文件: %s", log_file)
    return log_file


def get_logger(name: str) -> logging.Logger:
    """获取模块级 logger。"""
    return logging.getLogger(name)


def _hook_excepthook() -> None:
    """钩住 sys.excepthook，记录未捕获异常到日志。"""
    original = sys.excepthook

    def excepthook(exc_type, exc_value, exc_tb):
        logger = get_logger("unhandled")
        logger.critical(
            "未捕获异常",
            exc_info=(exc_type, exc_value, exc_tb),
        )
        # 仍然调用原始 hook（打印到 stderr）
        if original is not None and original != excepthook:
            with suppress(Exception):
                original(exc_type, exc_value, exc_tb)

    sys.excepthook = excepthook

    # 也钩住 threading 的异常
    original_threading = threading.excepthook

    def threading_excepthook(args):
        logger = get_logger("threading")
        logger.critical(
            "线程未捕获异常 (thread=%s)",
            args.thread.name if args.thread else "?",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )
        if (
            original_threading is not None
            and original_threading != threading_excepthook
        ):
            with suppress(Exception):
                original_threading(args)

    threading.excepthook = threading_excepthook


def _hook_tkinter_error() -> None:
    """钩住 Tk 的异常报告机制（report_callback_exception）。"""
    original = getattr(tkinter.Tk, "report_callback_exception", None)

    def report_callback_exception(self, exc, val, tb):
        logger = get_logger("tkinter")
        logger.critical(
            "Tkinter 回调异常: %s: %s",
            exc.__name__ if exc else "?",
            val,
        )
        logger.debug("详细回溯", exc_info=(exc, val, tb))
        if original is not None and original != report_callback_exception:
            with suppress(Exception):
                original(self, exc, val, tb)

    # 类型忽略: tkinter 的签名在各版本不一致
    tkinter.Tk.report_callback_exception = report_callback_exception  # type: ignore[assignment]


def add_console_handler(level: int = logging.INFO) -> None:
    """添加控制台日志输出（用于非 pythonw 模式）。"""
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, _LOG_DATE_FORMAT))
    handler.setLevel(level)
    logging.getLogger().addHandler(handler)


def is_initialized() -> bool:
    """日志系统是否已初始化。"""
    return _LOGGER_INITIALIZED
