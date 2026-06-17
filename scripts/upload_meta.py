#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-
"""上传元数据 — 从 _version.py 导入所有公共 API。

此文件保持薄层，所有真实逻辑在 `_version.py` 中。
"""

from __future__ import annotations

from scripts._version import (
    _EXE_VERSION,
    _VERSION,
    _VERSION_PATTERN,
    build_commit_message,
    bump_minor,
    bump_patch,
    classify_changed_paths,
    ensure_summary_marker_assignments,
    get_exe_version,
    get_version,
    parse_semver,
    please_read_me_path,
    read_exe_version,
    read_summary_for_commit,
    read_version,
    remove_summary_block,
    strip_summary_block,
    summarize_changes,
    write_summary_block,
    write_version,
)

__all__ = [
    "_EXE_VERSION",
    "_VERSION",
    "_VERSION_PATTERN",
    "build_commit_message",
    "bump_minor",
    "bump_patch",
    "classify_changed_paths",
    "ensure_summary_marker_assignments",
    "get_exe_version",
    "get_version",
    "parse_semver",
    "please_read_me_path",
    "read_exe_version",
    "read_summary_for_commit",
    "read_version",
    "remove_summary_block",
    "strip_summary_block",
    "summarize_changes",
    "write_summary_block",
    "write_version",
]
