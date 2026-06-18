# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""图像预处理管线：放大、锐化、灰度增强（不二值化，保留细节供 EasyOCR）。"""

from __future__ import annotations

from PIL import Image, ImageFilter, ImageOps

from wanna_understanding.logger import get_logger

from .profiles import EditorOCRProfile

log = get_logger(__name__)

# 无硬性最大边限制，让 EasyOCR 自行处理大图
_MAX_OCR_EDGE = 4800


class ImagePreprocessor:
    """OCR 前的图像预处理链。

    核心思路：尽量保留图像细节（不二值化），只做放大、锐化、增强对比度，
    让 EasyOCR 利用灰度层次信息做出更好的识别。
    """

    def upscale(self, image: Image.Image, factor: float = 2.0) -> Image.Image:
        """放大图像，提升小字号 OCR 准确率。"""
        factor = max(1.0, factor)
        new_size = (int(image.width * factor), int(image.height * factor))
        enlarged = image.resize(new_size, Image.Resampling.LANCZOS)
        return self._clamp_size(enlarged)

    def _clamp_size(
        self, image: Image.Image, max_edge: int = _MAX_OCR_EDGE
    ) -> Image.Image:
        """限制最长边，避免极端大图导致 OOM。"""
        width, height = image.size
        longest = max(width, height)
        if longest <= max_edge:
            return image
        scale = max_edge / longest
        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        return image.resize(new_size, Image.Resampling.LANCZOS)

    def sharpen(self, image: Image.Image) -> Image.Image:
        """锐化，增强字符边缘清晰度。"""
        return image.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))

    def grayscale(self, image: Image.Image) -> Image.Image:
        """转为灰度图。"""
        return ImageOps.grayscale(image)

    def enhance_contrast(self, image: Image.Image) -> Image.Image:
        """自动拉伸对比度，使文字更突出。"""
        return ImageOps.autocontrast(image, cutoff=2)

    def process(
        self,
        image: Image.Image,
        is_dark_theme: bool = False,
        profile: EditorOCRProfile | None = None,
    ) -> Image.Image:
        """执行完整预处理管线。

        不再进行二值化——二值化会丢失灰度细节，导致 EasyOCR 识别率下降。
        改为：放大 → 锐化 → 灰度 → 对比度增强 → 可选反色。
        """
        factor = profile.upscale_factor if profile else 3.0
        result = self.upscale(image, factor=factor)
        result = self.sharpen(result)
        result = self.grayscale(result)
        result = self.enhance_contrast(result)
        if is_dark_theme:
            # 深色模式：白字黑底 → 黑字白底（EasyOCR 对黑字白底识别更好）
            result = ImageOps.invert(result)
        return result
