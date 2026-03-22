"""
Document layout reconstruction from PaddleOCR boxes: HTML with absolute positioning,
approximate font size from bbox height, ink color from darkest pixels in each region.
"""
from __future__ import annotations

import html as html_lib
from typing import Any

import numpy as np


def bbox_to_xywh(box: list) -> tuple[float, float, float, float]:
    """Quad polygon → axis-aligned (x, y, w, h) in pixel space."""
    try:
        xs = [float(p[0]) for p in box]
        ys = [float(p[1]) for p in box]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        return x0, y0, max(0.0, x1 - x0), max(0.0, y1 - y0)
    except Exception:
        return 0.0, 0.0, 0.0, 0.0


def _infer_ink_color_bgr(crop_bgr: np.ndarray) -> tuple[int, int, int]:
    """Darkest fraction of pixels → approximate text/ink RGB (for light backgrounds)."""
    if crop_bgr is None or crop_bgr.size == 0:
        return 26, 26, 26
    if len(crop_bgr.shape) == 2:
        # Grayscale: dark = ink
        g = crop_bgr.reshape(-1)
        n = max(1, len(g) // 6)
        idx = np.argpartition(g, n)[:n]
        v = float(np.median(g[idx]))
        iv = int(max(0, min(255, v)))
        return iv, iv, iv
    b_ch, g_ch, r_ch = crop_bgr[:, :, 0], crop_bgr[:, :, 1], crop_bgr[:, :, 2]
    lum = 0.114 * b_ch + 0.587 * g_ch + 0.299 * r_ch
    flat_l = lum.reshape(-1)
    flat_px = crop_bgr.reshape(-1, 3)
    n = max(1, len(flat_l) // 6)
    darkest = np.argpartition(flat_l, n)[:n]
    med = np.median(flat_px[darkest], axis=0)
    b, g, r = float(med[0]), float(med[1]), float(med[2])
    # Paper-heavy crop: ink still dark
    if np.median(flat_l) > 200:
        r, g, b = min(r, 80), min(g, 80), min(b, 80)
    return int(max(0, min(255, r))), int(max(0, min(255, g))), int(max(0, min(255, b)))


def sample_ink_color_hex(bgr: np.ndarray, x: float, y: float, w: float, h: float) -> str:
    import cv2

    if bgr is None or bgr.size == 0:
        return "#1a1a1a"
    H, W = bgr.shape[:2]
    xi0 = max(0, int(x))
    yi0 = max(0, int(y))
    xi1 = min(W, int(round(x + w)))
    yi1 = min(H, int(round(y + h)))
    if xi1 <= xi0 or yi1 <= yi0:
        return "#1a1a1a"
    crop = bgr[yi0:yi1, xi0:xi1]
    if crop.size == 0:
        return "#1a1a1a"
    # Slight dilate to catch stroke edges on binary scans
    try:
        if len(crop.shape) == 2:
            crop_bgr = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
        else:
            crop_bgr = crop
    except Exception:
        crop_bgr = crop if len(crop.shape) == 3 else crop
    r, g, b = _infer_ink_color_bgr(crop_bgr)
    return f"#{r:02x}{g:02x}{b:02x}"


def build_absolute_layout_html(
    bgr: np.ndarray,
    line_items: list[dict[str, Any]],
    img_w: int,
    img_h: int,
) -> str:
    """
    One div per OCR box, position:absolute in a root matching image dimensions.
    line_items: { "text", "bbox", "confidence" } as from paddle_extract_structured.
    """
    parts: list[str] = [
        f'<div class="ocr-visual" data-ocr-layout="1" style="position:relative;'
        f"width:{int(img_w)}px;height:{int(img_h)}px;margin:0 auto;"
        f'background:#ffffff;box-sizing:border-box;overflow:hidden;">'
    ]
    for item in line_items:
        text = (item.get("text") or "").strip()
        box = item.get("bbox")
        if not text or not box:
            continue
        x, y, w, h = bbox_to_xywh(box)
        if w < 0.5 or h < 0.5:
            continue
        fs = max(8.0, min(96.0, h * 0.82))
        color = sample_ink_color_hex(bgr, x, y, w, h)
        et = html_lib.escape(text)
        parts.append(
            f'<div style="position:absolute;left:{x:.2f}px;top:{y:.2f}px;'
            f"width:{w:.2f}px;min-height:{h:.2f}px;font-size:{fs:.1f}px;"
            f"line-height:1.05;color:{color};white-space:pre-wrap;word-break:break-word;"
            f'font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;">{et}</div>'
        )
    parts.append("</div>")
    return "\n".join(parts)
