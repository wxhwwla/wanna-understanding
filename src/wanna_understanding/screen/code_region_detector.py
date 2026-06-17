# SPDX-License-Identifier: AGPL-3.0
# -*- coding: utf-8 -*-

"""智能代码区域检测：通过像素密度分析自动定位编辑器中的代码区。

工作原理：
  1. 将截图缩放到统一宽度，加快处理速度
  2. 转为灰度图，沿垂直方向检测每一行的"文字密度"
  3. 代码区域的特征：密集且均匀的水平文字行，高边缘密度
  4. 非代码区域的特征：稀疏文字（文件树）、大块空白（终端/面板）

用法：
    from wanna_understanding.screen.code_region_detector import detect_code_region
    rect = detect_code_region(screenshot)
    # rect = (left, top, right, bottom) — 截图中的像素坐标
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageFilter

from wanna_understanding.logger import get_logger

log = get_logger(__name__)

# 扫描参数
_SCAN_WIDTH = 300          # 缩放到此宽度进行快速分析
_H_SCAN_BANDS = 30         # 垂直方向分成多少条带
_MIN_TEXT_LINE_HEIGHT = 8  # 最小文字行高度(px)
_EDGE_THRESHOLD = 30       # 边缘检测阈值


@dataclass
class RegionLayout:
    """检测到的屏幕区域布局。"""

    code_rect: tuple[int, int, int, int]  # (left, top, right, bottom)
    has_file_tree: bool = False
    has_sidebar: bool = False
    has_terminal: bool = False
    full_size: tuple[int, int] = (0, 0)

    @property
    def code_width(self) -> int:
        return self.code_rect[2] - self.code_rect[0]

    @property
    def code_height(self) -> int:
        return self.code_rect[3] - self.code_rect[1]


def infer_layout(
    code_rect: tuple[int, int, int, int],
    image_size: tuple[int, int],
) -> RegionLayout:
    """根据检测到的代码区域推断周围布局。"""
    w, h = image_size
    left_pct = code_rect[0] / w if w > 0 else 0
    right_pct = code_rect[2] / w if w > 0 else 1
    bottom_pct = code_rect[3] / h if h > 0 else 1

    return RegionLayout(
        code_rect=code_rect,
        has_file_tree=left_pct > 0.08,   # 左侧空出 >8% → 有文件树
        has_sidebar=right_pct < 0.85,    # 右侧不足 85% → 有侧面板
        has_terminal=bottom_pct < 0.78,  # 底部不足 78% → 有终端
        full_size=image_size,
    )


def _find_code_top(
    scores: list[float],
    skip_top_bands: int = 1,
    threshold: float = 0.20,
    min_span: int = 2,
) -> int | None:
    """找到代码区的顶部条带索引。

    跳过最上面的 skip_top_bands 个条带（标题栏/标签栏区域），
    然后找到第一个连续密度 > threshold 的条带区域起点。
    """
    for i in range(skip_top_bands, len(scores)):
        if i + min_span <= len(scores) and all(
            s >= threshold for s in scores[i:i + min_span]
        ):
            return i
    return None


def _find_code_bottom(
    scores: list[float],
    code_top_band: int,
    orig_height: int,
    gap_threshold: float = 0.08,
    min_gap_bands: int = 3,
) -> int | None:
    """从 code_top_band 向下扫描，找到代码区底部。

    当连续 min_gap_bands 个条带密度低于 gap_threshold（空白间隙）
    时认为代码区结束（例如终端/状态栏的开始）。

    Returns:
        底部像素坐标，或 None（未找到明显间隙）
    """
    gap_count = 0
    for i in range(code_top_band + 1, len(scores)):
        if scores[i] < gap_threshold:
            gap_count += 1
            if gap_count >= min_gap_bands:
                # 找到间隙，返回前一个条带底部
                band_h = orig_height / len(scores)
                return int((i - min_gap_bands) * band_h)
        else:
            gap_count = 0
    return None


def detect_code_region(
    image: Image.Image,
    *,
    fallback_ratio: float = 0.70,
) -> tuple[int, int, int, int]:
    """智能检测截图中的代码区域，返回 (left, top, right, bottom) 像素坐标。

    如果检测失败，回退到取中间 fallback_ratio 比例的保守策略。

    Args:
        image: 原始截图
        fallback_ratio: 检测失败时的回退裁剪比例

    Returns:
        (left, top, right, bottom) 像素坐标
    """
    orig_w, orig_h = image.size
    if orig_w < 100 or orig_h < 100:
        log.debug("截图太小 (%dx%d)，跳过智能检测", orig_w, orig_h)
        return _center_crop_rect(orig_w, orig_h, fallback_ratio)

    # Pass 1：水平投影分析
    band_map = _analyze_horizontal_bands(image)

    # Pass 2：找到代码区顶部（跳过工具栏/标签栏，找到第一个密集文字区）
    band_code_top = _find_code_top(band_map)
    if band_code_top is None:
        log.debug("未找到代码区顶部，使用回退策略")
        return _center_crop_rect(orig_w, orig_h, fallback_ratio)
    band_h_px = orig_h / _H_SCAN_BANDS

    # 从顶部向下延伸：覆盖大部分编辑器区域（顶部到底部 75% 处）
    code_top_px = int(band_code_top * band_h_px)
    # 跳过最顶部 5%（标题栏/标签栏），最多不要超过 100px
    skip_top = min(int(orig_h * 0.04), 100)
    code_top_px = max(code_top_px, skip_top)
    # 向下延伸到画面 78% 处（跳过底部终端/状态栏）
    extend_bottom = int(orig_h * 0.78)
    # 但如果检测到高密度区域中断（终端开始），在中断处停下
    code_bottom_px = _find_code_bottom(band_map, band_code_top, orig_h)
    if code_bottom_px is None or code_bottom_px < code_top_px + 50:
        code_bottom_px = extend_bottom
    code_bottom_px = min(code_bottom_px, orig_h)

    log.debug("垂直范围: top=%d band=%d, bottom=%d (原始高=%d)",
               code_top_px, band_code_top, code_bottom_px, orig_h)

    # Pass 3：在该区域内做垂直投影，找代码区的左右边界
    cropped = image.crop((0, code_top_px, orig_w, code_bottom_px))
    code_left, code_right = _detect_horizontal_bounds(cropped)
    if code_left is None or code_right is None:
        log.debug("水平边界检测失败，使用回退策略")
        return _center_crop_rect(orig_w, orig_h, fallback_ratio)

    # 最终区域：放宽余量（保证不切到代码）
    code_rect_h = code_bottom_px - code_top_px
    margin_x = max(10, (code_right - code_left) // 15)
    margin_y = max(10, code_rect_h // 20)
    result = (
        max(0, code_left - margin_x),
        max(0, code_top_px - margin_y),
        min(orig_w, code_right + margin_x),
        min(orig_h, code_bottom_px + margin_y),
    )

    log.debug(
        "智能检测代码区: (%d,%d,%d,%d) 回退=%s",
        result[0], result[1], result[2], result[3],
        fallback_ratio,
    )
    return result


def _analyze_horizontal_bands(image: Image.Image) -> list[float]:
    """将截图分为水平条带，计算每个条带的文字密度分数。

    返回 H_SCAN_BANDS 个分数（0=空白, 1=最密集）。
    """
    import numpy as np

    orig_w, orig_h = image.size
    scale = _SCAN_WIDTH / orig_w
    thumb_h = int(orig_h * scale)
    thumb = image.resize((_SCAN_WIDTH, thumb_h), Image.Resampling.LANCZOS)

    # 边缘检测 + 灰度
    edges = thumb.convert("L").filter(ImageFilter.Kernel(
        (3, 3),
        [-1, -1, -1, -1, 8, -1, -1, -1, -1],
        scale=1, offset=0,
    ))
    arr = np.asarray(edges, dtype=np.float32)

    band_h = max(1, thumb_h // _H_SCAN_BANDS)
    scores: list[float] = []
    for i in range(_H_SCAN_BANDS):
        y0 = i * band_h
        y1 = min(thumb_h, y0 + band_h)
        band = arr[y0:y1, :]
        # 边缘密度：边缘像素比例
        edge_pixels = float(np.sum(band > _EDGE_THRESHOLD))
        total_pixels = float(band.size)
        density = edge_pixels / total_pixels if total_pixels > 0 else 0.0
        scores.append(density)

    # 归一化到 0~1
    max_score = max(scores) if scores else 1.0
    if max_score > 0:
        scores = [s / max_score for s in scores]

    log.debug("水平条带密度: %s", [f"{s:.2f}" for s in scores])
    return scores


def _detect_horizontal_bounds(
    cropped: Image.Image,
) -> tuple[int | None, int | None]:
    """在裁剪区域内做垂直投影，找到代码的左右边界。"""
    import numpy as np

    # 缩放到扫描宽度以加快处理
    cw, ch = cropped.size
    thumb_h = max(1, int(ch * _SCAN_WIDTH / cw))
    thumb = cropped.resize((_SCAN_WIDTH, thumb_h), Image.Resampling.LANCZOS)
    gray = thumb.convert("L")
    arr = np.asarray(gray, dtype=np.float32)

    # 每列的"文字强度"
    col_strength = 255.0 - arr.mean(axis=0)  # shape: (_SCAN_WIDTH,)

    # 平滑
    window = max(3, _SCAN_WIDTH // 40)
    kernel = np.ones(window) / window
    col_strength = np.convolve(col_strength, kernel, mode="same")

    # 找有效范围：强度 > 最大值的 15%
    threshold = col_strength.max() * 0.15
    strong_cols = np.where(col_strength > threshold)[0]

    if len(strong_cols) < 5:
        return None, None

    # 映射回原始图片坐标
    scale_to_orig = cw / _SCAN_WIDTH
    left_col = int(strong_cols[0] * scale_to_orig)
    right_col = int(strong_cols[-1] * scale_to_orig)

    return left_col, right_col


def _center_crop_rect(
    width: int, height: int, ratio: float = 0.70,
) -> tuple[int, int, int, int]:
    """回退策略：取中间比例。"""
    margin_w = int(width * (1 - ratio) / 2)
    margin_h = int(height * (1 - ratio) / 2)
    return (
        margin_w,
        margin_h,
        width - margin_w,
        height - margin_h,
    )
