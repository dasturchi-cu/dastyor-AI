"""
DASTYOR AI — Server-Side Render Service
========================================
Guarantees that PDF and Word exports are visually identical to
the browser/Telegram-Mini-App preview by rendering the SAME
Jinja2 template server-side.

Pipeline
--------
  form data (JSON)
    → _build_cv_context()    (normalise field names)
    → Jinja2 render           (cv_template.html)
    → WeasyPrint              (→ PDF bytes)      … or
    → html-to-docx / blob     (→ DOCX bytes)
"""

from __future__ import annotations

import logging
import os
import re
import time
import asyncio
from pathlib import Path

_HEX_ACCENT_RE = re.compile(r"^#[0-9A-Fa-f]{3,8}$")


def _sanitize_hex_accent(raw: dict) -> str:
    ac = str(raw.get("accent_color") or raw.get("cvColor") or "#3b82f6").strip()
    return ac if _HEX_ACCENT_RE.match(ac) else "#3b82f6"

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

# Small TTL cache for generated CV PDFs (speedup on repeated sends)
_CV_PDF_CACHE: dict[str, tuple[float, bytes]] = {}
_CV_PDF_CACHE_TTL_SECONDS = float(os.getenv("CV_PDF_CACHE_TTL_SECONDS", "30") or "30")
_CV_PDF_CACHE_MAX = int(os.getenv("CV_PDF_CACHE_MAX", "32") or "32")


def _cv_pdf_cache_key(html_str: str, base_url: str | None) -> str:
    import hashlib

    h = hashlib.sha256()
    h.update((base_url or "").encode("utf-8", "ignore"))
    h.update(b"\n")
    h.update(html_str.encode("utf-8", "ignore"))
    return h.hexdigest()


def _cv_pdf_cache_get(key: str) -> bytes | None:
    if _CV_PDF_CACHE_TTL_SECONDS <= 0:
        return None
    try:
        now = time.monotonic()
        hit = _CV_PDF_CACHE.get(key)
        if not hit:
            return None
        if (now - float(hit[0])) > _CV_PDF_CACHE_TTL_SECONDS:
            _CV_PDF_CACHE.pop(key, None)
            return None
        return hit[1]
    except Exception:
        return None


def _cv_pdf_cache_set(key: str, pdf: bytes) -> None:
    if _CV_PDF_CACHE_TTL_SECONDS <= 0:
        return
    try:
        if not pdf:
            return
        if len(_CV_PDF_CACHE) >= max(4, _CV_PDF_CACHE_MAX):
            oldest = sorted(_CV_PDF_CACHE.items(), key=lambda kv: kv[1][0])[
                : max(1, len(_CV_PDF_CACHE) - _CV_PDF_CACHE_MAX + 1)
            ]
            for k, _v in oldest:
                _CV_PDF_CACHE.pop(k, None)
        _CV_PDF_CACHE[key] = (time.monotonic(), pdf)
    except Exception:
        pass

# ── Template environment ───────────────────────────────────────────────────
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)

# ── Playwright (Pixel-perfect PDF from HTML) ───────────────────────────────
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_OK = True
    logger.info("Playwright: available ✅")
except ImportError:
    PLAYWRIGHT_OK = False
    logger.warning("Playwright not installed — PDF will fall back to WeasyPrint")

# ── WeasyPrint (Pure-Python PDF fallback) ──────────────────────────────────
try:
    from weasyprint import HTML as WeasyHTML
    WEASYPRINT_OK = True
    logger.info("WeasyPrint: available ✅")
except Exception:
    WEASYPRINT_OK = False
    logger.warning("WeasyPrint not available — PDF will use Playwright or xhtml2pdf fallback")

# ── xhtml2pdf (pure-Python fallback) ───────────────────────────────────────
try:
    from xhtml2pdf import pisa as _xhtml2pdf_pisa
    XHTML2PDF_OK = True
    logger.info("xhtml2pdf: available ✅")
except ImportError:
    XHTML2PDF_OK = False

_PW_INSTALL_ATTEMPTED = False

# Playwright browser pool — reuse Chromium across PDF requests (avoids cold launch ~2–5s)
_pw_manager = None
_pw_browser = None
_pw_browser_lock: asyncio.Lock | None = None
_pw_browser_uses = 0
_PW_BROWSER_MAX_USES = max(10, int(os.getenv("PLAYWRIGHT_BROWSER_MAX_USES", "40") or "40"))


def _browser_lock() -> asyncio.Lock:
    global _pw_browser_lock
    if _pw_browser_lock is None:
        _pw_browser_lock = asyncio.Lock()
    return _pw_browser_lock


async def _get_shared_browser():
    """Return a warm Chromium instance; recycle after N PDF renders."""
    global _pw_manager, _pw_browser, _pw_browser_uses
    if not PLAYWRIGHT_OK:
        return None
    async with _browser_lock():
        needs_new = (
            _pw_browser is None
            or not _pw_browser.is_connected()
            or _pw_browser_uses >= _PW_BROWSER_MAX_USES
        )
        if needs_new:
            if _pw_browser is not None:
                try:
                    await _pw_browser.close()
                except Exception:
                    pass
            if _pw_manager is not None:
                try:
                    await _pw_manager.stop()
                except Exception:
                    pass
            _pw_manager = await async_playwright().start()
            _pw_browser = await _pw_manager.chromium.launch(
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ]
            )
            _pw_browser_uses = 0
            logger.info("Playwright: warm browser launched (pool)")
        _pw_browser_uses += 1
        return _pw_browser

# Production: WeasyPrint tez; Playwright og'ir. Railway'da build vaqtida chromium o'rnatish yaxshi.
def _playwright_disabled(*, cv_pdf: bool = False) -> bool:
    """
    Global o‘chirish: barcha HTML→PDF (masalan Obyektivka fallback).
    CV uchun alohida: jonli preview iframe = Chromium, PDF ham Chromium bo‘lmasa
    WeasyPrint bilan dizayn 1:1 bo‘lmaydi. Shuning uchun CV defaultda global
    DISABLE ni e’tiborsiz qoldiradi — faqat DISABLE_PLAYWRIGHT_CV_PDF=1 Weasy ga majbur qiladi.
    """
    if cv_pdf:
        return os.getenv("DISABLE_PLAYWRIGHT_CV_PDF", "").strip().lower() in ("1", "true", "yes", "on")
    return os.getenv("DISABLE_PLAYWRIGHT_PDF", "").strip().lower() in ("1", "true", "yes", "on")


def _playwright_auto_install_allowed() -> bool:
    return os.getenv("PLAYWRIGHT_AUTO_INSTALL", "").strip().lower() in ("1", "true", "yes", "on")


def _maybe_install_playwright_chromium() -> None:
    """
    Best-effort: ensure Playwright Chromium is installed.
    Some deployments install the python package but not the browser binaries,
    which causes runtime 500s for PDF exports.
    """
    global _PW_INSTALL_ATTEMPTED
    if _PW_INSTALL_ATTEMPTED or not _playwright_auto_install_allowed():
        return
    _PW_INSTALL_ATTEMPTED = True
    try:
        import subprocess
        import sys

        logger.warning("Playwright Chromium missing? Attempting install...")
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("Playwright install attempted.")
    except Exception as e:
        logger.warning("Playwright install attempt failed: %s", e)


# ═══════════════════════════════════════════════════════════════════════════
# DATA NORMALISATION
# ═══════════════════════════════════════════════════════════════════════════

def _parse_items(raw: list[dict]) -> list[dict]:
    """
    Normalize experience/education records from the webapp payload.
    Webapp sends: {title, company, date, desc}  OR  {pos, co, yr, d}
    CV builder (cv.html) sends experience as {from, to, description}.
    """
    out = []
    for r in raw:
        title = (
            r.get("title")
            or r.get("pos")
            or r.get("position")
            or r.get("description")
            or r.get("d")
            or ""
        )
        company = (
            r.get("company")
            or r.get("co")
            or r.get("institution")
            or r.get("place")
            or ""
        )
        date = r.get("date") or r.get("yr") or r.get("year") or ""
        if not date and (r.get("from") or r.get("to")):
            date = f"{r.get('from') or ''}-{r.get('to') or ''}".strip("-")
        out.append({
            "title": title,
            "company": company,
            "date": date,
            "desc": r.get("desc") or r.get("d") or r.get("description") or "",
        })
    return out


def _normalize_language_levels(raw: list) -> list[dict]:
    out: list[dict] = []
    for r in raw or []:
        if not isinstance(r, dict):
            continue

        def _lvl(key: str) -> int:
            try:
                v = int(r.get(key) or 0)
            except (TypeError, ValueError):
                v = 0
            return max(0, min(6, v))

        out.append(
            {
                "lang": str(r.get("lang") or "").strip(),
                "listen": _lvl("listen"),
                "read": _lvl("read"),
                "speak": _lvl("speak"),
                "write": _lvl("write"),
            }
        )
    return out


def _normalize_cv_achievements(raw: list) -> list[dict]:
    out: list[dict] = []
    for r in raw or []:
        if not isinstance(r, dict):
            continue
        out.append(
            {
                "type": str(r.get("type") or "").strip(),
                "title": str(r.get("title") or "").strip(),
                "year": str(r.get("year") or "").strip(),
            }
        )
    return out


def build_cv_context(raw: dict) -> dict:
    """
    Build a clean template context dict from raw API form payload.
    Keys match the Jinja2 template variables in cv_template.html.
    """
    skills_raw: str = raw.get("skills", "") or ""
    skills = [s.strip() for s in skills_raw.replace(",", "\n").splitlines() if s.strip()]

    # Support works[] from webapp OR work_experience[] from bot
    works_raw = raw.get("works") or raw.get("work_experience") or []
    edu_raw   = raw.get("education_list") or raw.get("education") or []

    lang_raw = (
        raw.get("languages_list")
        or raw.get("language_levels")
        or raw.get("langData")
        or []
    )
    ach_raw = (
        raw.get("achievements_list")
        or raw.get("cv_achievements")
        or raw.get("achData")
        or []
    )

    return {
        "template":    raw.get("template", "minimal").lower(),
        "lang":        raw.get("lang", "uz_lat"),
        "name":        raw.get("name", ""),
        "role":        raw.get("spec", "") or raw.get("role", ""),
        "phone":       raw.get("phone", ""),
        "email":       raw.get("email", ""),
        "loc":         raw.get("loc", "") or raw.get("place", ""),
        "about":       raw.get("about", ""),
        "img":         raw.get("img", "") or "",   # absolute URL or base64
        "skills":      skills,
        "experiences": _parse_items(works_raw),
        "education":   _parse_items(edu_raw),
        "language_levels": _normalize_language_levels(lang_raw if isinstance(lang_raw, list) else []),
        "achievements": _normalize_cv_achievements(ach_raw if isinstance(ach_raw, list) else []),
        "accent_color": _sanitize_hex_accent(raw),
    }


def build_obyektivka_context(raw: dict) -> dict:
    """Build template context for Obyektivka template (paid/export — clean)."""
    from backend.services.document_render.context import build_obyektivka_render_context

    return build_obyektivka_render_context(
        raw,
        watermark=bool(raw.get("watermark")),
        mask_pii=bool(raw.get("mask_pii")),
        process_photo=True,
    )


# ═══════════════════════════════════════════════════════════════════════════
# HTML RENDERING
# ═══════════════════════════════════════════════════════════════════════════

def render_cv_html(data: dict) -> str:
    """Render cv_template.html with given CV data dict. Returns HTML string."""
    ctx = build_cv_context(data) if "template" in data else data
    tmpl = _jinja_env.get_template("cv_template.html")
    return tmpl.render(data=ctx)


def render_obyektivka_html(
    data: dict,
    *,
    watermark: bool | None = None,
    mask_pii: bool | None = None,
) -> str:
    """Render obyektivka_template.html — single source for preview and PDF."""
    from backend.services.document_render.context import build_obyektivka_render_context

    if "render" in data and "fullname" not in data:
        ctx = data
    else:
        wm = watermark if watermark is not None else bool(data.get("watermark"))
        mp = mask_pii if mask_pii is not None else bool(data.get("mask_pii"))
        ctx = build_obyektivka_render_context(
            data,
            watermark=wm,
            mask_pii=mp,
            process_photo=True,
        )
    tmpl = _jinja_env.get_template("obyektivka_template.html")
    return tmpl.render(data=ctx)


# ═══════════════════════════════════════════════════════════════════════════
# PDF GENERATION  (Playwright - Pixel Perfect)
# ═══════════════════════════════════════════════════════════════════════════

async def _pdf_bytes_weasy(html_str: str, base_url: str | None) -> bytes | None:
    """Fast path: no browser startup (target ~2–3s total pipeline)."""
    if not WEASYPRINT_OK:
        return None
    try:
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: WeasyHTML(string=html_str, base_url=base_url).write_pdf(
                optimize_images=False,
            ),
        )
    except Exception as e:
        logger.warning("WeasyPrint PDF failed: %s", e)
        return None


async def _pdf_bytes_xhtml2pdf(html_str: str) -> bytes | None:
    """Last-resort PDF backend — works without GTK/Chromium."""
    if not XHTML2PDF_OK:
        return None
    try:
        import asyncio
        import io

        def _render() -> bytes | None:
            buf = io.BytesIO()
            status = _xhtml2pdf_pisa.CreatePDF(html_str, dest=buf, encoding="utf-8")
            if status.err:
                return None
            return buf.getvalue()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _render)
    except Exception as e:
        logger.warning("xhtml2pdf PDF failed: %s", e)
        return None


async def _html_pdf_playwright(html_str: str, *, cv_pdf: bool = False, print_media: bool = False) -> bytes | None:
    """Chromium print — veb-preview (iframe) bilan bir xil dvigatel; shriftlar va CSS yaqinroq."""
    if _playwright_disabled(cv_pdf=cv_pdf):
        return None
    if not PLAYWRIGHT_OK:
        return None
    # Tarmoq shriftlari (Google Fonts) + katta HTML: domcontentloaded yetarli emas
    font_wait_ms = 450 if cv_pdf else 200
    content_timeout_ms = 90_000 if cv_pdf else 60_000
    media = "print" if print_media else "screen"

    async def _once():
        browser = await _get_shared_browser()
        if browser is None:
            return None
        page = await browser.new_page()
        try:
            if cv_pdf:
                # A4 @ 96dpi — preview iframe bilan bir xil kenglik, siqilish oldini oladi
                await page.set_viewport_size({"width": 794, "height": 1123})
            try:
                await page.emulate_media(media=media)
            except Exception:
                pass
            await page.set_content(
                html_str,
                wait_until="load",
                timeout=content_timeout_ms,
            )
            try:
                await page.evaluate(
                    "async () => { if (document.fonts && document.fonts.ready) await document.fonts.ready; }"
                )
            except Exception:
                pass
            await page.wait_for_timeout(font_wait_ms)
            pdf_bytes = await page.pdf(
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
                scale=1,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )
            return pdf_bytes
        finally:
            try:
                await page.close()
            except Exception:
                pass

    try:
        out = await _once()
        logger.info("HTML→PDF generated via Playwright")
        return out
    except Exception as e:
        logger.warning("Playwright PDF failed: %s", e)
        if _playwright_auto_install_allowed():
            logger.warning("PLAYWRIGHT_AUTO_INSTALL=1 — chromium o'rnatishga urinilmoqda (sekin)")
            _maybe_install_playwright_chromium()
            try:
                out = await _once()
                logger.info("HTML→PDF generated via Playwright (after install)")
                return out
            except Exception as e2:
                logger.warning("Playwright retry failed: %s", e2)
        return None


async def generate_cv_pdf(data: dict, base_url: str | None = None) -> bytes | None:
    """
    Render CV template → PDF bytes.
    Default: Playwright (Chromium) first — veb-preview (iframe) bilan bir xil dvigatel, 1:1 yaqin.
    WeasyPrint: CV_PDF_PLAYWRIGHT_FIRST=0 bo'lsa birinchi yoki Playwright muvaffaqiyatsiz bo'lsa.
    """
    html_str = render_cv_html(data)

    bu = (base_url or "").strip().rstrip("/")
    if bu and "<head>" in html_str:
        html_str = html_str.replace("<head>", f"<head><base href='{bu}/'>")

    ck = _cv_pdf_cache_key(html_str, bu or None)
    cached = _cv_pdf_cache_get(ck)
    if cached:
        logger.info("CV PDF cache hit (%s bytes)", len(cached))
        return cached

    pw_first = os.getenv("CV_PDF_PLAYWRIGHT_FIRST", "1").strip().lower() in ("1", "true", "yes", "on")

    if pw_first:
        pdf_pw = await _html_pdf_playwright(html_str, cv_pdf=True)
        if pdf_pw:
            logger.info("CV PDF generated via Playwright (preview bilan moslashtirilgan)")
            _cv_pdf_cache_set(ck, pdf_pw)
            return pdf_pw
        pdf_fast = await _pdf_bytes_weasy(html_str, bu or None)
        if pdf_fast:
            logger.warning(
                "CV PDF: WeasyPrint ishlatildi (Playwright yo‘q yoki xato). "
                "Jonli ko‘rinish bilan rang/font/layout farqi bo‘lishi mumkin — "
                "Chromium o‘rnatilganini va DISABLE_PLAYWRIGHT_CV_PDF=0 ekanini tekshiring."
            )
            logger.info("CV PDF generated via WeasyPrint (fallback)")
            _cv_pdf_cache_set(ck, pdf_fast)
            return pdf_fast
    else:
        pdf_fast = await _pdf_bytes_weasy(html_str, bu or None)
        if pdf_fast:
            logger.info("CV PDF generated via WeasyPrint (fast path)")
            _cv_pdf_cache_set(ck, pdf_fast)
            return pdf_fast
        pdf_pw = await _html_pdf_playwright(html_str, cv_pdf=True)
        if pdf_pw:
            _cv_pdf_cache_set(ck, pdf_pw)
            return pdf_pw

    pdf_xhtml = await _pdf_bytes_xhtml2pdf(html_str)
    if pdf_xhtml:
        logger.info("CV PDF generated via xhtml2pdf (fallback)")
        _cv_pdf_cache_set(ck, pdf_xhtml)
        return pdf_xhtml

    logger.error("All PDF backends failed for CV")
    return None


async def generate_obyektivka_pdf(
    data: dict,
    base_url: str | None = None,
    *,
    watermark: bool = False,
    mask_pii: bool = False,
) -> bytes | None:
    """
    Render Obyektivka template → PDF bytes.
    watermark/mask_pii=True — test preview PDF (@DastyorAiBot orqasida).
    """
    html_str = render_obyektivka_html(data, watermark=watermark, mask_pii=mask_pii)

    bu = (base_url or "").strip().rstrip("/")
    if bu and "<head>" in html_str:
        html_str = html_str.replace("<head>", f"<head><base href='{bu}/'>")

    pw_first = os.getenv("OBY_PDF_PLAYWRIGHT_FIRST", os.getenv("CV_PDF_PLAYWRIGHT_FIRST", "1")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    if pw_first:
        pdf_pw = await _html_pdf_playwright(html_str, cv_pdf=True, print_media=True)
        if pdf_pw:
            logger.info("Obyektivka PDF generated via Playwright (print layout, 2 sahifa)")
            return pdf_pw
        pdf_fast = await _pdf_bytes_weasy(html_str, bu or None)
        if pdf_fast:
            logger.warning(
                "Obyektivka PDF: WeasyPrint ishlatildi (Playwright yo‘q yoki xato). "
                "Jonli ko‘rinish bilan farq bo‘lishi mumkin."
            )
            return pdf_fast
    else:
        pdf_fast = await _pdf_bytes_weasy(html_str, bu or None)
        if pdf_fast:
            logger.info("Obyektivka PDF generated via WeasyPrint (fast path)")
            return pdf_fast
        pdf_pw = await _html_pdf_playwright(html_str, cv_pdf=True, print_media=True)
        if pdf_pw:
            logger.info("Obyektivka PDF generated via Playwright")
            return pdf_pw

    logger.error("All PDF backends failed for Obyektivka")
    return None


# ═══════════════════════════════════════════════════════════════════════════
# WORD (.doc) GENERATION  — MS Word HTML format
# ═══════════════════════════════════════════════════════════════════════════

_WORD_WRAPPER = """\
<html xmlns:o='urn:schemas-microsoft-com:office:office'
      xmlns:w='urn:schemas-microsoft-com:office:word'
      xmlns='http://www.w3.org/TR/REC-html40'>
<head>
  <meta charset='utf-8'>
  <xml>
    <w:WordDocument>
      <w:View>Print</w:View>
      <w:Zoom>100</w:Zoom>
      <w:DoNotOptimizeForBrowser/>
    </w:WordDocument>
  </xml>
  <style>
    @page WordSection1 {{ size: 210mm 297mm; margin: 15mm; }}
    div.WordSection1  {{ page: WordSection1; }}
    /* Word: convert flex → table for column layouts */
    .tpl-split, .tpl-creative {{
      display: table !important; width: 100% !important;
    }}
    .tpl-split .sidebar, .tpl-creative .left {{
      display: table-cell !important; vertical-align: top !important;
    }}
    .tpl-split .main, .tpl-creative .right {{
      display: table-cell !important; vertical-align: top !important;
    }}
    .tpl-modern .body, .tpl-elegant .body-cols, .tpl-corporate .body-cols {{
      display: table !important; width: 100% !important;
    }}
    .tpl-modern .col-main, .tpl-elegant .col-main, .tpl-corporate .col-main {{
      display: table-cell !important; vertical-align: top !important;
    }}
    .tpl-modern .col-side, .tpl-elegant .col-side, .tpl-corporate .col-side {{
      display: table-cell !important; vertical-align: top !important;
    }}
    {extra_css}
  </style>
</head>
<body>
  <div class="WordSection1">{body_html}</div>
</body>
</html>"""


def generate_cv_word(data: dict, extra_css: str = "") -> bytes:
    """
    Render CV HTML → .doc blob (MS Word HTML format).
    Returns UTF-8 BOM + HTML bytes.  Filename extension should be .doc.
    """
    inner_html = render_cv_html(data)
    word_html = _WORD_WRAPPER.format(body_html=inner_html, extra_css=extra_css)
    return b"\xef\xbb\xbf" + word_html.encode("utf-8")


def generate_obyektivka_word(data: dict, extra_css: str = "") -> bytes:
    """Render Obyektivka HTML → .doc blob bytes."""
    inner_html = render_obyektivka_html(data)
    word_html = _WORD_WRAPPER.format(body_html=inner_html, extra_css=extra_css)
    return b"\xef\xbb\xbf" + word_html.encode("utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE: safe name for filenames
# ═══════════════════════════════════════════════════════════════════════════

def safe_filename(name: str, max_len: int = 30) -> str:
    return (name or "doc").replace(" ", "_").replace("/", "_")[:max_len]
