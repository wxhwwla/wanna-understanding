# SPDX-License-Identifier: AGPL-3.0

"""编辑器主题检测：根据截图亮度判断深色/浅色模式。"""

from __future__ import annotations

from PIL import Image


def detect_dark_theme(image: Image.Image, threshold: int = 128) -> bool:
    """根据平均亮度判断是否为深色主题。

    Args:
        image: 截图或预处理前的图像。
        threshold: 灰度均值低于该值视为深色主题。

    Returns:
        True 表示深色主题，应对 OCR 做反色预处理。
    """
    gray = image.convert("L")
    pixels = list(gray.get_flattened_data())
    count = len(pixels)
    if count == 0:
        return False
    return (sum(pixels) / count) < threshold
