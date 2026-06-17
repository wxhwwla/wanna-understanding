# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""预下载 EasyOCR 模型。

改编自 endfield_damage_calculator/tools/ocr/download_models.py。
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

_EASYOCR_CACHE = Path.home() / ".EasyOCR" / "model"

REQUIRED_MODELS: list[dict[str, str]] = [
    {
        "name": "craft_mlt_25k",
        "filename": "craft_mlt_25k.pth",
        "zip_url": (
            "https://github.com/JaidedAI/EasyOCR/releases/download/"
            "pre-v1.1.6/craft_mlt_25k.zip"
        ),
    },
    {
        "name": "english_g2",
        "filename": "english_g2.pth",
        "zip_url": (
            "https://github.com/JaidedAI/EasyOCR/releases/download/v1.3/english_g2.zip"
        ),
    },
]


def _download(url: str, dest: Path, mirror: bool) -> None:
    if mirror:
        url = f"https://ghproxy.net/{url}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": "wanna-understanding/ocr"})
    with urlopen(request, timeout=120) as response, dest.open("wb") as handle:
        handle.write(response.read())


def _extract(zip_path: Path, target_dir: Path) -> None:
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(target_dir)
    zip_path.unlink(missing_ok=True)


def download_all(*, mirror: bool = False) -> int:
    """下载缺失的 EasyOCR 模型，返回失败数量。"""
    _EASYOCR_CACHE.mkdir(parents=True, exist_ok=True)
    failures = 0
    for item in REQUIRED_MODELS:
        target = _EASYOCR_CACHE / item["filename"]
        if target.is_file():
            print(f"[ok] {item['name']} 已存在")
            continue
        zip_path = _EASYOCR_CACHE / f"{item['filename']}.zip"
        print(f"[download] {item['name']} …")
        try:
            _download(item["zip_url"], zip_path, mirror=mirror)
            _extract(zip_path, _EASYOCR_CACHE)
            print(f"[ok] {item['name']}")
        except Exception as exc:
            failures += 1
            print(f"[error] {item['name']}: {exc}")
    return failures


def verify_models() -> bool:
    """检查英文 OCR 所需模型是否齐全。"""
    missing = [
        item["name"]
        for item in REQUIRED_MODELS
        if not (_EASYOCR_CACHE / item["filename"]).is_file()
    ]
    if missing:
        print("缺少模型:", ", ".join(missing))
        return False
    print("EasyOCR 模型齐全")
    return True


def main(argv: list[str] | None = None) -> int:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(description="预下载 EasyOCR 模型")
    parser.add_argument("--mirror", action="store_true", help="通过 ghproxy 镜像下载")
    parser.add_argument("--verify", action="store_true", help="仅校验本地模型")
    args = parser.parse_args(argv)
    if args.verify:
        return 0 if verify_models() else 1
    return 0 if download_all(mirror=args.mirror) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
