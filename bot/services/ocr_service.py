"""
OCR Service Module (Async Optimized)
Handles Image-to-Text conversion using Gemini asynchronously to prevent blocking.
Uses a dedicated thread pool so OCR never blocks other bot features.
"""
import html
import logging
import asyncio
import os
import re
from functools import partial
import tempfile
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from typing import Any

warnings.filterwarnings(
    "ignore",
    message=".*google.generativeai.*",
    category=DeprecationWarning,
)

import google.generativeai as genai
from google.generativeai.types import HarmBlockThreshold, HarmCategory
from PIL import Image

from config import GOOGLE_API_KEY

logger = logging.getLogger(__name__)

# Dedicated thread pool for OCR tasks — prevents blocking other bot features
_ocr_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ocr")

# OCR timeout (seconds) — prevents the bot from hanging on slow Gemini responses
# Keep default lower to avoid "2 minutes stuck"; can be increased via env.
OCR_TIMEOUT = max(25, int(os.getenv("OCR_TIMEOUT_SECONDS", "70")))

# Hujjat OCR uchun — Gemini tez-tez xavfsizlik bilan bo'sh javob qaytaradi
_OCR_SAFETY = [
    {"category": HarmCategory.HARM_CATEGORY_HARASSMENT, "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH},
    {"category": HarmCategory.HARM_CATEGORY_HATE_SPEECH, "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH},
    {"category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH},
    {"category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH},
]

def _bbox_poly_to_xyxy(box: Any) -> tuple[float, float, float, float]:
    """
    Paddle/Gemini OCR bbox can be quad polygon; normalize to axis-aligned xyxy.
    Returns (x0, y0, x1, y1).
    """
    try:
        pts = box or []
        xs = [float(p[0]) for p in pts]
        ys = [float(p[1]) for p in pts]
        if not xs or not ys:
            return 0.0, 0.0, 0.0, 0.0
        return min(xs), min(ys), max(xs), max(ys)
    except Exception:
        return 0.0, 0.0, 0.0, 0.0


def _cluster_positions(vals: list[float], tol: float) -> list[float]:
    """1D clustering by proximity; returns sorted cluster centers."""
    if not vals:
        return []
    s = sorted(float(v) for v in vals)
    out: list[list[float]] = []
    cur: list[float] = [s[0]]
    for v in s[1:]:
        if abs(v - cur[-1]) <= tol:
            cur.append(v)
        else:
            out.append(cur)
            cur = [v]
    out.append(cur)
    centers = [sum(g) / float(len(g)) for g in out if g]
    centers.sort()
    return centers


def _nearest_index(centers: list[float], v: float) -> int:
    if not centers:
        return 0
    # centers sorted; linear scan is fine (small N)
    best_i = 0
    best_d = abs(v - centers[0])
    for i in range(1, len(centers)):
        d = abs(v - centers[i])
        if d < best_d:
            best_d = d
            best_i = i
    return best_i


def _paddle_grid_env_int(name: str, default: int, *, vmin: int, vmax: int) -> int:
    try:
        v = int(os.getenv(name, str(default)))
        return max(vmin, min(vmax, v))
    except Exception:
        return max(vmin, min(vmax, default))


def _column_band_index(xc: float, col_edges: list[float], iw: int) -> int:
    """Map horizontal center to column using sorted left edges (bands to image width)."""
    ce = col_edges or [0.0]
    n = len(ce)
    iw_f = float(max(1, iw))
    if n == 1:
        return 0
    for i in range(n):
        left = float(ce[i])
        right = float(ce[i + 1]) if i + 1 < n else iw_f
        if i == n - 1:
            if xc >= left - 0.5:
                return i
        elif left <= xc < right:
            return i
    if xc < float(ce[0]):
        return 0
    return n - 1


def _build_grid_table_from_paddle_lines(lines: list[dict[str, Any]], img_w: int, img_h: int) -> str:
    """
    Heuristic: cluster bbox x/y to infer columns/rows, then map text into cells.
    This is meant for ledger/forms where explicit grid exists.
    """
    if not lines:
        return ""
    iw = max(1, int(img_w))
    ih = max(1, int(img_h))

    items: list[tuple[float, float, float, float, str]] = []
    for ln in lines:
        text = str((ln.get("text") or "")).strip()
        box = ln.get("bbox")
        if not text or not box:
            continue
        x0, y0, x1, y1 = _bbox_poly_to_xyxy(box)
        if x1 <= x0 or y1 <= y0:
            continue
        items.append((x0, y0, x1, y1, text))

    min_items = _paddle_grid_env_int("OCR_PADDLE_GRID_MIN_ITEMS", 4, vmin=2, vmax=80)
    max_cols = _paddle_grid_env_int("OCR_PADDLE_GRID_MAX_COLS", 80, vmin=2, vmax=200)
    max_rows = _paddle_grid_env_int("OCR_PADDLE_GRID_MAX_ROWS", 160, vmin=2, vmax=500)
    max_cells = _paddle_grid_env_int("OCR_PADDLE_GRID_MAX_CELLS", 3000, vmin=100, vmax=80000)

    if len(items) < min_items:
        return ""

    # Cluster left edges for columns; top edges for rows.
    # Tolerances are relative to image size; tuned for scanned tables.
    try:
        x_frac = float(os.getenv("OCR_PADDLE_GRID_X_TOL_FRAC", "0.02") or "0.02")
    except Exception:
        x_frac = 0.02
    try:
        y_frac = float(os.getenv("OCR_PADDLE_GRID_Y_TOL_FRAC", "0.018") or "0.018")
    except Exception:
        y_frac = 0.018
    x_frac = max(0.004, min(0.08, x_frac))
    y_frac = max(0.004, min(0.08, y_frac))
    x_tol = max(6.0, iw * x_frac)
    y_tol = max(6.0, ih * y_frac)
    col_centers = _cluster_positions([x0 for x0, _, _, _, _ in items], tol=x_tol)
    row_centers = _cluster_positions([y0 for _, y0, _, _, _ in items], tol=y_tol)

    # Plausibility gates (avoid breaking non-table docs).
    if len(col_centers) < 2 or len(row_centers) < 2:
        return ""
    if len(col_centers) > max_cols or len(row_centers) > max_rows:
        return ""
    if len(col_centers) * len(row_centers) > max_cells:
        return ""

    # Column widths (percent): based on distance between centers.
    # Add a synthetic last boundary at image width for the last col.
    col_edges = col_centers[:]
    col_edges.sort()
    # Ensure first edge is near 0 for nicer widths
    if col_edges and col_edges[0] > iw * 0.05:
        col_edges = [0.0] + col_edges
    # Build approximate widths from consecutive edges; last to iw
    widths_px: list[float] = []
    for i in range(len(col_edges)):
        left = col_edges[i]
        right = col_edges[i + 1] if i + 1 < len(col_edges) else float(iw)
        widths_px.append(max(10.0, right - left))
    total_w = sum(widths_px) or float(iw)
    widths_pct = [max(1.0, 100.0 * w / total_w) for w in widths_px]

    n_rows = len(row_centers)
    n_cols = len(widths_pct)

    grid: list[list[str]] = [["" for _ in range(n_cols)] for _ in range(n_rows)]
    for x0, y0, x1, y1, text in items:
        xc = (x0 + x1) * 0.5
        yc = (y0 + y1) * 0.5
        ri = _nearest_index(row_centers, yc)
        ci = _column_band_index(xc, col_edges, iw)
        if ri < 0 or ri >= n_rows or ci < 0 or ci >= n_cols:
            continue
        cur = grid[ri][ci]
        grid[ri][ci] = (cur + ("\n" if cur else "") + text).strip()

    # Render HTML with strict borders; keep line breaks.
    parts: list[str] = []
    fs = "10px" if n_cols > 24 else "11px"
    parts.append(
        '<table style="border-collapse:collapse;width:100%;table-layout:fixed;'
        f'font-family:Arial,Helvetica,sans-serif;font-size:{fs};">'
    )
    for r in range(n_rows):
        parts.append("<tr>")
        for c in range(n_cols):
            w_attr = ""
            if r == 0:
                w_attr = f' width="{widths_pct[c]:.2f}%"'
            txt = (grid[r][c] or "").strip()
            if txt:
                safe = (
                    txt.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace("\r\n", "\n")
                    .replace("\r", "\n")
                )
                safe = "<br>".join(safe.split("\n"))
            else:
                safe = ""
            parts.append(
                f'<td{w_attr} style="border:1px solid #000;padding:2px 3px;'
                f'vertical-align:top;white-space:pre-wrap;word-break:break-word;">{safe}</td>'
            )
        parts.append("</tr>")
    parts.append("</table>")
    return "\n".join(parts)


def _extract_text_from_gemini_response(result) -> str:
    """result.text ba'zan bo'sh yoki xato; parts va finish_reason ni ham tekshiramiz."""
    if not result:
        return ""
    try:
        t = (result.text or "").strip()
        if t:
            return t
    except Exception as e:
        logger.warning("Gemini result.text o'qilmadi: %s", e)
    try:
        for c in getattr(result, "candidates", None) or []:
            content = getattr(c, "content", None)
            if not content:
                fr = getattr(c, "finish_reason", None)
                logger.info("Gemini: content yo'q, finish_reason=%s", fr)
                continue
            parts = getattr(content, "parts", None) or []
            chunks = [p.text for p in parts if getattr(p, "text", None)]
            if chunks:
                return "".join(chunks).strip()
            fr = getattr(c, "finish_reason", None)
            logger.info("Gemini: parts matnsiz, finish_reason=%s", fr)
    except Exception as e:
        logger.warning("Gemini parts ajratish xato: %s", e)
    try:
        pf = getattr(result, "prompt_feedback", None)
        if pf is not None:
            logger.info("Gemini prompt_feedback=%s block_reason=%s", pf, getattr(pf, "block_reason", None))
    except Exception:
        pass
    return ""


def _blocking_upload_path(path: str):
    try:
        myfile = genai.upload_file(path)
        waited = 0
        while myfile.state.name == "PROCESSING" and waited < 30:
            time.sleep(1)
            waited += 1
            try:
                myfile = genai.get_file(myfile.name)
            except Exception:
                break
        return myfile
    except Exception as e:
        logger.error("OCR upload failed: %s", e)
        return None


def _normalize_image_to_png_sync(src_path: str) -> str | None:
    """Telegram/WebP/RGBA va noto'g'ri kengaytma uchun bitta PNG."""
    try:
        with Image.open(src_path) as im:
            im = im.convert("RGB")
            fd, out = tempfile.mkstemp(suffix=".png", prefix="ocr_norm_")
            os.close(fd)
            im.save(out, "PNG", optimize=True)
            return out
    except Exception as e:
        logger.warning("OCR PNG normalize failed %s: %s", src_path, e)
        return None


def _enhance_image_for_ocr_sync(src_path: str) -> str | None:
    """
    Improve OCR accuracy by enhancing contrast/sharpness and upscaling.
    This helps Gemini read faint lines, stamps, and small text.
    """
    try:
        from PIL import ImageEnhance, ImageFilter, ImageOps
    except Exception:
        return None
    try:
        with Image.open(src_path) as im:
            im = im.convert("RGB")
            # Upscale (keeps small fonts readable)
            try:
                scale = float(os.getenv("OCR_UPSCALE", "1.8") or "1.8")
            except Exception:
                scale = 1.8
            scale = max(1.0, min(3.0, scale))
            if scale > 1.01:
                w, h = im.size
                im = im.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
            # Auto-contrast and slight brightness boost
            im = ImageOps.autocontrast(im, cutoff=1)
            im = ImageEnhance.Contrast(im).enhance(1.55)
            im = ImageEnhance.Brightness(im).enhance(1.06)
            # Mild denoise then sharpen edges / lines
            im = im.filter(ImageFilter.MedianFilter(size=3))
            im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=190, threshold=2))

            # Optional: binarize for handwriting/ledger tables (often improves digits)
            bin_on = os.getenv("OCR_BINARIZE", "1").strip().lower() not in {"0", "false", "no", "off"}
            if bin_on:
                g = ImageOps.grayscale(im)
                # Adaptive-ish threshold (fast): use histogram percentile
                hist = g.histogram()
                total = sum(hist) or 1
                acc = 0
                thr = 160
                target = int(total * 0.62)
                for i, v in enumerate(hist):
                    acc += v
                    if acc >= target:
                        thr = i
                        break
                thr = max(90, min(200, int(thr)))
                bw = g.point(lambda p: 255 if p > thr else 0, mode="1")
                im = bw.convert("RGB")
            fd, out = tempfile.mkstemp(suffix=".png", prefix="ocr_enh_")
            os.close(fd)
            im.save(out, "PNG", optimize=True)
            return out
    except Exception as e:
        logger.info("OCR enhance skipped %s: %s", src_path, e)
        return None


def _extract_layout_with_paddle_sync(image_path: str) -> str:
    """Best-effort: local Paddle layout HTML for stronger 1:1 numbering/placement."""
    try:
        from backend.services.paddle_ocr_runtime import ocr_extract_text_from_bytes
    except Exception:
        return ""
    try:
        with open(image_path, "rb") as f:
            raw = f.read()
        out = ocr_extract_text_from_bytes(raw) or {}
        return str(out.get("html_layout") or "").strip()
    except Exception as e:
        logger.info("Paddle layout OCR unavailable/fail path=%s: %s", image_path, e)
        return ""


def _layout_html_quality_ok(layout_html: str) -> bool:
    """
    Heuristic gate:
    - Agar savolnoma/list hujjatda raqamlar tushib qolsa, Paddle layoutni rad etib Gemini'ga o'tamiz.
    """
    h = (layout_html or "").strip()
    if len(h) < 80:
        return False
    txt = re.sub(r"<[^>]+>", " ", h)
    txt = re.sub(r"\s+", " ", txt).strip()
    if len(txt) < 40:
        return False
    qmarks = txt.count("?")
    numbered = len(re.findall(r"\b\d{1,2}\.\s", txt))
    if qmarks >= 4 and numbered <= 1:
        return False
    return True


async def extract_text_from_image(image_path: str) -> str:
    """
    Extracts text from an image file using Gemini asynchronously.
    Forces 1:1 HTML layout preservation. Does not block the event loop.
    """
    skip_gemini = os.getenv("OCR_SKIP_GEMINI", "0").strip().lower() in {
        "1", "true", "yes", "on",
    }
    if not GOOGLE_API_KEY and not skip_gemini:
        return ""

    t0 = time.perf_counter()
    norm_png: str | None = None
    upload_from_norm_only = False
    try:
        logger.info("OCR extract started path=%s", image_path)

        loop = asyncio.get_running_loop()
        # Optional: strict table reconstruction from PaddleOCR boxes (no Gemini).
        paddle_table_on = os.getenv("OCR_PADDLE_TABLE_GRID", "0").strip().lower() not in {
            "0", "false", "no", "off",
        }
        if paddle_table_on:
            try:
                # PaddleOCR requires `paddle` (paddlepaddle). If missing, skip instantly.
                try:
                    import paddle  # type: ignore  # noqa: F401
                except Exception:
                    paddle = None
                if paddle is None:
                    raise ImportError("paddle (paddlepaddle) not installed")

                import cv2  # type: ignore

                bgr = cv2.imread(image_path, cv2.IMREAD_COLOR)
                if bgr is not None and getattr(bgr, "size", 0):
                    from backend.services.paddle_ocr_runtime import (
                        paddle_extract_structured,
                        warmup_paddle_engine_async,
                        is_paddle_engine_ready,
                        is_paddle_warmup_done,
                    )
                    # Warm up engine in background so next requests are fast.
                    warmup_paddle_engine_async()
                    # If models are still downloading / warmup not done, don't block user flow.
                    # Keep OCR responsive (<5s) by skipping Paddle-table until engine is ready.
                    if not is_paddle_engine_ready() and not is_paddle_warmup_done():
                        raise TimeoutError("Paddle warmup in progress; skip table grid for now")

                    table_timeout = max(
                        3,
                        int(os.getenv("OCR_PADDLE_TABLE_GRID_TIMEOUT_SECONDS", "5")),
                    )
                    try:
                        structured = await asyncio.wait_for(
                            loop.run_in_executor(
                                _ocr_executor,
                                partial(paddle_extract_structured, bgr, include_html_layout=False),
                            ),
                            timeout=float(table_timeout),
                        )
                    except asyncio.TimeoutError:
                        structured = None
                        logger.info(
                            "Paddle table grid timed out (%ss), fallback to Gemini path=%s",
                            table_timeout,
                            image_path,
                        )
                    lines = (structured or {}).get("lines") or []
                    iw = int((structured or {}).get("width") or bgr.shape[1])
                    ih = int((structured or {}).get("height") or bgr.shape[0])
                    html_table = _build_grid_table_from_paddle_lines(lines, iw, ih)
                    if html_table:
                        logger.info(
                            "OCR table reconstructed via Paddle boxes in %.1fs path=%s",
                            time.perf_counter() - t0,
                            image_path,
                        )
                        return html_table
            except Exception as pe:
                logger.debug("Paddle table grid path failed: %s", pe)

        # Default OFF: Paddle layout often doesn't map 1:1 into DOCX (absolute divs stretch).
        prefer_paddle_layout = os.getenv("OCR_BOT_PREFER_PADDLE_LAYOUT", "0").strip().lower() not in {
            "0", "false", "no", "off",
        }
        paddle_html_last = ""
        if prefer_paddle_layout:
            paddle_html_last = await loop.run_in_executor(
                _ocr_executor, _extract_layout_with_paddle_sync, image_path
            )
            if paddle_html_last and _layout_html_quality_ok(paddle_html_last):
                logger.info("OCR done via Paddle layout in %.1fs path=%s", time.perf_counter() - t0, image_path)
                return paddle_html_last
            if paddle_html_last:
                logger.info("Paddle layout quality low, fallback to Gemini path=%s", image_path)

        if skip_gemini:
            if not (paddle_html_last or "").strip():
                paddle_html_last = (
                    await loop.run_in_executor(
                        _ocr_executor, _extract_layout_with_paddle_sync, image_path
                    )
                    or ""
                )
            if paddle_html_last and paddle_html_last.strip():
                logger.info(
                    "OCR skip_gemini: using Paddle layout (no quality gate) in %.1fs path=%s",
                    time.perf_counter() - t0,
                    image_path,
                )
                return paddle_html_last
            try:
                from backend.services.paddle_ocr_runtime import ocr_extract_text_from_bytes

                def _paddle_plain() -> dict[str, Any]:
                    with open(image_path, "rb") as f:
                        return ocr_extract_text_from_bytes(f.read()) or {}

                out = await loop.run_in_executor(_ocr_executor, _paddle_plain)
                plain = (out.get("text") or "").strip()
                if plain:
                    logger.info(
                        "OCR skip_gemini: plain Paddle text in %.1fs path=%s",
                        time.perf_counter() - t0,
                        image_path,
                    )
                    return (
                        '<div class="ocr-plain" style="white-space:pre-wrap">'
                        f"{html.escape(plain)}</div>"
                    )
            except Exception as pe:
                logger.info("OCR skip_gemini paddle plain failed path=%s: %s", image_path, pe)
            return ""

        # Enhance image for OCR (optional but ON by default)
        enhance_on = os.getenv("OCR_ENHANCE_IMAGE", "1").strip().lower() not in {"0", "false", "no", "off"}
        upload_path = image_path
        enh_png: str | None = None
        if enhance_on:
            enh_png = await loop.run_in_executor(_ocr_executor, _enhance_image_for_ocr_sync, image_path)
            if enh_png and os.path.exists(enh_png):
                upload_path = enh_png

        myfile = await loop.run_in_executor(_ocr_executor, _blocking_upload_path, upload_path)
        if not myfile or myfile.state.name == "FAILED":
            logger.warning("Gemini upload as-is failed, trying PNG normalize path=%s", image_path)
            myfile = None

        if not myfile:
            norm_png = await loop.run_in_executor(_ocr_executor, _normalize_image_to_png_sync, image_path)
            if norm_png:
                myfile = await loop.run_in_executor(_ocr_executor, _blocking_upload_path, norm_png)
                if myfile and myfile.state.name != "FAILED":
                    upload_from_norm_only = True
            if not myfile or myfile.state.name == "FAILED":
                logger.error("Gemini file upload/processing failed (incl. PNG retry).")
                return ""

        # Use fallback model list — don't hardcode a single model
        from bot.services.ai_service import get_model
        model = await get_model()
        if not model:
            logger.error("No Gemini model available for OCR.")
            return ""

        prompt = """You are an OCR engine. Your output MUST be a 1:1 replica of the document.
Return ONLY valid HTML. No markdown fences. No explanations. No extra text.

NON-NEGOTIABLE:
1) Do NOT summarize, translate, normalize, or "fix" anything.
2) Copy EXACT characters (including commas vs dots in numbers), punctuation, casing, and symbols.
3) Preserve the document structure and the relative placement of content.
4) NEVER drop content. If unreadable: write [?] in that exact place.

THIS DOCUMENT IS VERY LIKELY A LEDGER / TABLE:
- If you see any grid/table/form: output HTML <table> (NEVER absolute-positioned divs).
- The table MUST match the grid 1:1:
  - exact number of columns and rows
  - correct rowspan/colspan
  - empty cells must remain empty: <td></td>
  - handwritten values must go into the correct cell
- You MUST show borders for EVERY cell so the grid looks like the source.

REQUIRED HTML TEMPLATE (follow this style strictly):
<table style="border-collapse:collapse;width:100%;table-layout:fixed;font-family:Arial,Helvetica,sans-serif;font-size:11px;">
  <tr>
    <td style="border:1px solid #000;padding:2px 3px;vertical-align:top;white-space:pre-wrap;word-break:break-word;">...</td>
  </tr>
</table>

WIDTHS:
- Set column widths on the first row using width="..%" or style="width:..%".
- Keep widths consistent across rows.

NUMBERS / HANDWRITING:
- Handwritten digits are important. Read them carefully.
- Keep decimals exactly as in the image (e.g., 12,5 vs 12.5).
- Keep leading zeros and minus signs if present.
- If a digit is ambiguous, keep the cell but use [?] for the ambiguous part (example: 1[?]3).

TEXT RULES:
- Keep line breaks inside a cell with <br>.
- Use <b>/<i>/<u> ONLY if the source is bold/italic/underlined.
- Use alignment styles ONLY when clearly visible.

OUTPUT RULE:
- Output HTML only. Start immediately with the first element. End after the last element.
"""

        def _run_generation(mf):
            return model.generate_content(
                [mf, prompt],
                safety_settings=_OCR_SAFETY,
                generation_config={"temperature": 0.1},
            )

        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(_ocr_executor, _run_generation, myfile),
                timeout=OCR_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.error("OCR timeout path=%s after %.1fs (limit=%ss)", image_path, time.perf_counter() - t0, OCR_TIMEOUT)
            result = None

        # Cleanup uploaded file in background
        def _cleanup(name):
            try:
                genai.delete_file(name)
            except Exception:
                pass

        loop.run_in_executor(_ocr_executor, _cleanup, myfile.name)

        text = _extract_text_from_gemini_response(result)
        if text:
            text = text.replace("```html", "").replace("```", "").strip()
            logger.info("OCR done in %.1fs path=%s", time.perf_counter() - t0, image_path)
            return text

        # Retry once with a stricter prompt for forms/tables (often fixes "cho'zilib ketdi" outputs)
        retry_on = os.getenv("OCR_GEMINI_RETRY", "1").strip().lower() not in {"0", "false", "no", "off"}
        if retry_on:
            strict_prompt = (
                prompt
                + "\n\nEXTRA STRICT RETRY:\n"
                + "- Output ONLY tables. No paragraphs unless the source has non-table text.\n"
                + "- For grids: create the full table even if some cells are blank.\n"
                + "- Use borders on EVERY cell (border:1px solid #000).\n"
                + "- NEVER drop a row/column. If unsure: use [?] in that cell.\n"
                + "- Preserve headers/side labels exactly where they appear.\n"
                + "- Do NOT merge cells unless the grid visually merges (rowspan/colspan must match).\n"
                + "- Prefer multiple tables (in order) ONLY if the source has clearly separated blocks/pages.\n"
            )

            def _run_generation_strict(mf):
                return model.generate_content(
                    [mf, strict_prompt],
                    safety_settings=_OCR_SAFETY,
                    generation_config={"temperature": 0.0},
                )

            try:
                result_s = await asyncio.wait_for(
                    loop.run_in_executor(_ocr_executor, _run_generation_strict, myfile),
                    timeout=OCR_TIMEOUT,
                )
            except asyncio.TimeoutError:
                result_s = None
            text_s = _extract_text_from_gemini_response(result_s)
            if text_s:
                text_s = text_s.replace("```html", "").replace("```", "").strip()
                logger.info("OCR strict retry success in %.1fs path=%s", time.perf_counter() - t0, image_path)
                return text_s

        # Birinchi muvaffaqiyatli upload asl fayl bo'lsa, lekin matn bo'sh — RGB PNG qayta urinish
        if not text and not upload_from_norm_only:
            if not norm_png:
                norm_png = await loop.run_in_executor(_ocr_executor, _normalize_image_to_png_sync, image_path)
        if not text and not upload_from_norm_only and norm_png:
            mf2 = await loop.run_in_executor(_ocr_executor, _blocking_upload_path, norm_png)
            if mf2 and mf2.state.name != "FAILED":
                try:
                    result2 = await asyncio.wait_for(
                        loop.run_in_executor(_ocr_executor, _run_generation, mf2),
                        timeout=OCR_TIMEOUT,
                    )
                except asyncio.TimeoutError:
                    result2 = None
                loop.run_in_executor(_ocr_executor, _cleanup, mf2.name)
                text2 = _extract_text_from_gemini_response(result2)
                if text2:
                    text2 = text2.replace("```html", "").replace("```", "").strip()
                    logger.info("OCR (2nd PNG try) done in %.1fs path=%s", time.perf_counter() - t0, image_path)
                    return text2

    except Exception as e:
        logger.error("OCR failed path=%s after %.1fs: %s", image_path, time.perf_counter() - t0, e, exc_info=True)
    finally:
        if norm_png and os.path.isfile(norm_png):
            try:
                os.remove(norm_png)
            except Exception:
                pass
        try:
            if "enh_png" in locals() and enh_png and os.path.isfile(enh_png):
                os.remove(enh_png)
        except Exception:
            pass

    return ""
