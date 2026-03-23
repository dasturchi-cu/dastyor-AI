"""
Document layout reconstruction from PaddleOCR boxes: HTML with absolute positioning,
approximate font size from bbox height, ink color from darkest pixels in each region.
"""
from __future__ import annotations

import html as html_lib
import statistics
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
    Har bir OCR qutisi: foiz bilan absolute joylashuv — konteyner kengayganda/siqlganda
    nisbat saqlanadi (px faqat bitta o‘lchamda ishonchli).

    Root: width:100% + max-width + aspect-ratio — real rasm proporsiyasi.
    Matn: left/top/width/min-height — foiz; shrift: container query cqh (balandlik nisbati).
    """
    iw = max(1, int(img_w))
    ih = max(1, int(img_h))
    # Foizlar — bbox va OCR ishlatilgan rasm (iw x ih) bilan bir xil koordinata tizimi
    parts: list[str] = [
        f'<div class="ocr-visual" data-ocr-layout="1" style="'
        f"container-type:size;position:relative;box-sizing:border-box;"
        f"width:100%;max-width:{iw}px;aspect-ratio:{iw} / {ih};"
        f"margin:0 auto;background:#ffffff;overflow:hidden;"
        f'-webkit-text-size-adjust:100%;text-size-adjust:100%;">'
    ]
    nodes: list[dict[str, Any]] = []
    for item in line_items:
        text = (item.get("text") or "").strip()
        box = item.get("bbox")
        if not text or not box:
            continue
        x, y, w, h = bbox_to_xywh(box)
        if w < 0.5 or h < 0.5:
            continue
        # Paddle ba'zan 1–2 px tashqarida qaytaradi — foizlar "sakrab" ketmasin
        x = min(max(0.0, x), float(iw - 1))
        y = min(max(0.0, y), float(ih - 1))
        w = min(w, float(iw) - x)
        h = min(h, float(ih) - y)
        if w < 0.5 or h < 0.5:
            continue
        fs = max(8.0, min(96.0, h * 0.82))
        color = sample_ink_color_hex(bgr, x, y, w, h)
        et = html_lib.escape(text)
        lp = 100.0 * x / iw
        tp = 100.0 * y / ih
        wp = 100.0 * w / iw
        hp = 100.0 * h / ih
        nodes.append(
            {
                "text": et,
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "fs": fs,
                "color": color,
                "lp": lp,
                "tp": tp,
                "wp": wp,
                "hp": hp,
            }
        )
    if not nodes:
        parts.append("</div>")
        return "\n".join(parts)

    # 1) Column detection (2-column docs): split by largest x gap between centers.
    # If no reliable split, keep a single column.
    col_boundary = None
    if len(nodes) >= 6:
        centers = sorted((n["x"] + n["w"] * 0.5) for n in nodes)
        gaps = [(centers[i + 1] - centers[i], i) for i in range(len(centers) - 1)]
        if gaps:
            max_gap, idx = max(gaps, key=lambda t: t[0])
            left_count = idx + 1
            right_count = len(centers) - left_count
            if max_gap > iw * 0.18 and left_count >= 2 and right_count >= 2:
                col_boundary = (centers[idx] + centers[idx + 1]) * 0.5

    for n in nodes:
        center_x = n["x"] + n["w"] * 0.5
        n["col"] = 0 if (col_boundary is None or center_x <= col_boundary) else 1

    # 2) Paragraph detection inside each column via vertical gap.
    grouped: list[tuple[int, list[dict[str, Any]]]] = []
    for col in (0, 1):
        col_nodes = [n for n in nodes if n["col"] == col]
        if not col_nodes:
            continue
        col_nodes.sort(key=lambda n: (n["y"], n["x"]))
        hs = [n["h"] for n in col_nodes if n["h"] > 0.1]
        median_h = statistics.median(hs) if hs else 14.0
        new_para_gap = max(8.0, median_h * 0.9)

        current: list[dict[str, Any]] = []
        last_bottom = None
        for n in col_nodes:
            if not current:
                current = [n]
                last_bottom = n["y"] + n["h"]
                continue
            gap = n["y"] - float(last_bottom or n["y"])
            if gap > new_para_gap:
                grouped.append((col, current))
                current = [n]
            else:
                current.append(n)
            last_bottom = max(float(last_bottom or 0.0), n["y"] + n["h"])
        if current:
            grouped.append((col, current))

    # 3) Render grouped paragraphs with absolute coordinates.
    for _, para_nodes in sorted(grouped, key=lambda t: (t[0], min(n["y"] for n in t[1]), min(n["x"] for n in t[1]))):
        p_x = min(n["x"] for n in para_nodes)
        p_y = min(n["y"] for n in para_nodes)
        p_r = max(n["x"] + n["w"] for n in para_nodes)
        p_b = max(n["y"] + n["h"] for n in para_nodes)
        p_w = max(1.0, p_r - p_x)
        p_h = max(1.0, p_b - p_y)
        p_lp = 100.0 * p_x / iw
        p_tp = 100.0 * p_y / ih
        p_wp = 100.0 * p_w / iw
        p_hp = 100.0 * p_h / ih

        p_fs = statistics.median([n["fs"] for n in para_nodes]) if para_nodes else 12.0
        p_cqh = 100.0 * p_fs / ih
        p_color = para_nodes[0]["color"] if para_nodes else "#1a1a1a"

        line_html: list[str] = []
        para_nodes = sorted(para_nodes, key=lambda n: (n["y"], n["x"]))
        prev_y = None
        for n in para_nodes:
            if prev_y is not None:
                dy = n["y"] - prev_y
                if dy > max(2.0, n["h"] * 0.33):
                    line_html.append("<br>")
            line_html.append(n["text"])
            prev_y = n["y"]

        parts.append(
            f'<div style="position:absolute;left:{p_lp:.5f}%;top:{p_tp:.5f}%;'
            f"width:{p_wp:.5f}%;min-height:{p_hp:.5f}%;"
            f"box-sizing:border-box;margin:0;padding:0;"
            f"font-size:{p_fs:.2f}px;font-size:calc(1cqh * {p_cqh:.6f});"
            f"line-height:1.15;color:{p_color};white-space:pre-wrap;word-break:break-word;"
            f"font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;overflow:hidden;"
            f'">{"".join(line_html)}</div>'
        )
    parts.append("</div>")
    return "\n".join(parts)
