# SPDX-License-Identifier: AGPL-3.0

"""PyInstaller 打包脚本 — 生成 Windows 可分发目录。"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def build(*, clean: bool = False, console: bool = False) -> int:
    """使用 PyInstaller 构建 onedir 发行包。"""
    root = Path(__file__).resolve().parent.parent
    entry = root / "src" / "wanna_understanding" / "__main__.py"
    dist = root / "dist" / "WannaUnderstanding"
    build_dir = root / "build" / "wanna_understanding"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        "WannaUnderstanding",
        "--onedir",
        "--noconfirm",
        "--paths",
        str(root / "src"),
        "--hidden-import",
        "easyocr",
        "--hidden-import",
        "pystray",
        "--hidden-import",
        "mss",
        "--collect-all",
        "easyocr",
        "--distpath",
        str(root / "dist"),
        "--workpath",
        str(build_dir),
        str(entry),
    ]
    if console:
        cmd.append("--console")
    else:
        cmd.append("--noconsole")
    if clean:
        cmd.insert(3, "--clean")
    print("[build]", " ".join(cmd))
    subprocess.run(cmd, cwd=root, check=True)
    print(f"[ok] 输出目录: {dist}")
    print("请将 .env 或 DEEPSEEK_API_KEY 配置在 exe 同目录后运行。")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="打包 Wanna Understanding")
    parser.add_argument("--clean", action="store_true", help="清理后再构建")
    parser.add_argument(
        "--console",
        action="store_true",
        help="保留控制台窗口（调试用，默认无控制台）",
    )
    args = parser.parse_args(argv)
    try:
        return build(clean=args.clean, console=args.console)
    except subprocess.CalledProcessError as exc:
        print(f"[error] PyInstaller 失败，退出码 {exc.returncode}")
        return exc.returncode or 1
    except ModuleNotFoundError:
        print('[error] 未安装 PyInstaller：pip install -e ".[build]"')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
