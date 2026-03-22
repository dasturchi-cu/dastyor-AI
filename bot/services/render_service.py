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
from pathlib import Path

_HEX_ACCENT_RE = re.compile(r"^#[0-9A-Fa-f]{3,8}$")


def _sanitize_hex_accent(raw: dict) -> str:
    ac = str(raw.get("accent_color") or raw.get("cvColor") or "#3b82f6").strip()
    return ac if _HEX_ACCENT_RE.match(ac) else "#3b82f6"

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

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
    logger.warning("WeasyPrint not installed — PDF will fall back to python-docx conversion")

_PW_INSTALL_ATTEMPTED = False

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
    """Build template context for Obyektivka template."""
    works = raw.get("work_experience", [])
    relatives = raw.get("relatives", [])
    return {
        "lang":           raw.get("lang", "uz_lat"),
        # Template uses d.img to render photo (absolute URL or data URL).
        # Webapp/API send photo as `photo_data` (data:image/...).
        "img":            raw.get("img", "") or raw.get("photo_data", "") or "",
        "fullname":       raw.get("fullname", ""),
        "birthdate":      raw.get("birthdate", "") or raw.get("birth", ""),
        "birthplace":     raw.get("birthplace", "") or raw.get("place", ""),
        "nation":         raw.get("nation", ""),
        "party":          raw.get("party", ""),
        "education":      raw.get("education", ""),
        "graduated":      raw.get("graduated", ""),
        "specialty":      raw.get("specialty", ""),
        "degree":         raw.get("degree", ""),
        "scientific_title": raw.get("scientific_title", ""),
        "languages":      raw.get("languages", ""),
        "military_rank":  raw.get("military_rank", ""),
        "awards":         raw.get("awards", ""),
        "deputy":         raw.get("deputy", ""),
        "address":        raw.get("address", ""),
        "phone":          raw.get("phone", ""),
        "work_experience": works,
        "relatives":       relatives,
    }


# ═══════════════════════════════════════════════════════════════════════════
# HTML RENDERING
# ═══════════════════════════════════════════════════════════════════════════

def render_cv_html(data: dict) -> str:
    """Render cv_template.html with given CV data dict. Returns HTML string."""
    ctx = build_cv_context(data) if "template" in data else data
    tmpl = _jinja_env.get_template("cv_template.html")
    return tmpl.render(data=ctx)


def render_obyektivka_html(data: dict) -> str:
    """Render obyektivka_template.html with given data dict. Returns HTML string."""
    ctx = build_obyektivka_context(data) if "fullname" in data else data
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
            lambda: WeasyHTML(string=html_str, base_url=base_url).write_pdf(),
        )
    except Exception as e:
        logger.warning("WeasyPrint PDF failed: %s", e)
        return None


async def _html_pdf_playwright(html_str: str, *, cv_pdf: bool = False) -> bytes | None:
    """Chromium print — veb-preview (iframe) bilan bir xil dvigatel; shriftlar va CSS yaqinroq."""
    if _playwright_disabled(cv_pdf=cv_pdf):
        return None
    if not PLAYWRIGHT_OK:
        return None
    # Tarmoq shriftlari (Google Fonts) + katta HTML: domcontentloaded yetarli emas
    font_wait_ms = 450 if cv_pdf else 200
    content_timeout_ms = 90_000 if cv_pdf else 60_000

    async def _once():
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ]
            )
            page = await browser.new_page()
            try:
                await page.emulate_media(media="screen")
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
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )
            await browser.close()
            return pdf_bytes

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

    pw_first = os.getenv("CV_PDF_PLAYWRIGHT_FIRST", "1").strip().lower() in ("1", "true", "yes", "on")

    if pw_first:
        pdf_pw = await _html_pdf_playwright(html_str, cv_pdf=True)
        if pdf_pw:
            logger.info("CV PDF generated via Playwright (preview bilan moslashtirilgan)")
            return pdf_pw
        pdf_fast = await _pdf_bytes_weasy(html_str, bu or None)
        if pdf_fast:
            logger.warning(
                "CV PDF: WeasyPrint ishlatildi (Playwright yo‘q yoki xato). "
                "Jonli ko‘rinish bilan rang/font/layout farqi bo‘lishi mumkin — "
                "Chromium o‘rnatilganini va DISABLE_PLAYWRIGHT_CV_PDF=0 ekanini tekshiring."
            )
            logger.info("CV PDF generated via WeasyPrint (fallback)")
            return pdf_fast
    else:
        pdf_fast = await _pdf_bytes_weasy(html_str, bu or None)
        if pdf_fast:
            logger.info("CV PDF generated via WeasyPrint (fast path)")
            return pdf_fast
        pdf_pw = await _html_pdf_playwright(html_str, cv_pdf=True)
        if pdf_pw:
            return pdf_pw

    logger.error("All PDF backends failed for CV")
    return None


async def generate_obyektivka_pdf(data: dict, base_url: str | None = None) -> bytes | None:
    """
    Render Obyektivka template → PDF bytes.
    Default: Playwright first (mini-app iframe bilan bir xil Chromium) — preview ≈ PDF.
    OBY_PDF_PLAYWRIGHT_FIRST=0 yoki WeasyPrint tez yo‘l.
    """
    html_str = render_obyektivka_html(data)

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
        pdf_pw = await _html_pdf_playwright(html_str, cv_pdf=True)
        if pdf_pw:
            logger.info("Obyektivka PDF generated via Playwright (preview bilan moslashtirilgan)")
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
        pdf_pw = await _html_pdf_playwright(html_str, cv_pdf=True)
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
