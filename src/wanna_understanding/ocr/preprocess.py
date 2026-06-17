# SPDX-License-Identifier: AGPL-3.0

"""图像预处理管线：放大、灰度、二值化与反色。"""

from __future__ import annotations

from PIL import Image, ImageOps

from .profiles import EditorOCRProfile

_MAX_OCR_EDGE = 1600


class ImagePreprocessor:
    """OCR 前的图像预处理链。"""

    def upscale(self, image: Image.Image, factor: float = 2.0) -> Image.Image:
        """放大图像，提升小字号 OCR 准确率。"""
        factor = max(1.0, factor)
        new_size = (int(image.width * factor), int(image.height * factor))
        enlarged = image.resize(new_size, Image.Resampling.LANCZOS)
        return self._clamp_size(enlarged)

    def _clamp_size(self, image: Image.Image, max_edge: int = _MAX_OCR_EDGE) -> Image.Image:
        """限制最长边，避免大图 OCR 在 CPU 上过慢。"""
        width, height = image.size
        longest = max(width, height)
        if longest <= max_edge:
            return image
        scale = max_edge / longest
        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        return image.resize(new_size, Image.Resampling.LANCZOS)

    def grayscale(self, image: Image.Image) -> Image.Image:
        """转为灰度图。"""
        return ImageOps.grayscale(image)

    def adaptive_threshold(self, image: Image.Image) -> int:
        """根据灰度中位数计算自适应二值化阈值。"""
        gray = image.convert("L")
        pixels = list(gray.get_flattened_data())
        if not pixels:
            return 128
        return int(sorted(pixels)[len(pixels) // 2])

    def binarize(self, image: Image.Image, threshold: int = 128) -> Image.Image:
        """二值化，减弱语法高亮背景干扰。"""
        gray = image.convert("L")
        pixels = gray.load()
        if pixels is None:
            return gray
        output = Image.new("L", gray.size)
        out_pixels = output.load()
        if out_pixels is None:
            return gray
        for y in range(gray.height):
            for x in range(gray.width):
                value = int(pixels[x, y])
                out_pixels[x, y] = 255 if value > threshold else 0
        return output

    def invert(self, image: Image.Image) -> Image.Image:
        """反色（深色模式：白字黑底 → 黑字白底）。"""
        if image.mode != "L":
            image = image.convert("L")
        return ImageOps.invert(image)

    def process(
        self,
        image: Image.Image,
        is_dark_theme: bool = False,
        profile: EditorOCRProfile | None = None,
    ) -> Image.Image:
        """执行完整预处理管线。"""
        factor = profile.upscale_factor if profile else 2.0
        result = self.upscale(image, factor=factor)
        result = self.grayscale(result)
        if is_dark_theme:
            result = self.invert(result)
        if profile and profile.binarize_threshold is not None:
            threshold = profile.binarize_threshold
        else:
            threshold = self.adaptive_threshold(result)
        return self.binarize(result, threshold=threshold)
