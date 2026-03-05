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

import io
import logging
import os
import time
from pathlib import Path
from typing import Any

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
    logger.warning("Playwright not installed — PDF will fall back to python-docx conversion")


# ═══════════════════════════════════════════════════════════════════════════
# DATA NORMALISATION
# ═══════════════════════════════════════════════════════════════════════════

def _parse_items(raw: list[dict]) -> list[dict]:
    """
    Normalize experience/education records from the webapp payload.
    Webapp sends: {title, company, date, desc}  OR  {pos, co, yr, d}
    """
    out = []
    for r in raw:
        out.append({
            "title":   r.get("title") or r.get("pos") or r.get("position") or "",
            "company": r.get("company") or r.get("co") or r.get("institution") or "",
            "date":    r.get("date") or r.get("yr") or r.get("year") or "",
            "desc":    r.get("desc") or r.get("d") or r.get("description") or "",
        })
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

    return {
        "template":    raw.get("template", "minimal").lower(),
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
    }


def build_obyektivka_context(raw: dict) -> dict:
    """Build template context for Obyektivka template."""
    works = raw.get("work_experience", [])
    relatives = raw.get("relatives", [])
    return {
        "fullname":       raw.get("fullname", ""),
        "birthdate":      raw.get("birthdate", "") or raw.get("birth", ""),
        "birthplace":     raw.get("birthplace", "") or raw.get("place", ""),
        "nation":         raw.get("nation", ""),
        "party":          raw.get("party", "Partiyasiz"),
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

async def generate_cv_pdf(data: dict, base_url: str | None = None) -> bytes | None:
    """
    Render CV template → PDF bytes via Headless Chromium (Playwright).
    Returns None if Playwright is not installed.
    """
    if not PLAYWRIGHT_OK:
        logger.warning("Playwright not available, PDF generation skipped")
        return None

    html_str = render_cv_html(data)
    
    # We must prepend a <base href="..."> if base_url is set so assets load correctly
    if base_url:
        if "<head>" in html_str:
            html_str = html_str.replace("<head>", f"<head><base href='{base_url}'>")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--no-sandbox', '--disable-setuid-sandbox'])
        page = await browser.new_page()
        await page.set_content(html_str, wait_until="networkidle")
        pdf_bytes = await page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}
        )
        await browser.close()
        return pdf_bytes


async def generate_obyektivka_pdf(data: dict, base_url: str | None = None) -> bytes | None:
    """Render Obyektivka template → PDF bytes via Headless Chromium."""
    if not PLAYWRIGHT_OK:
        return None

    html_str = render_obyektivka_html(data)
    
    if base_url:
        if "<head>" in html_str:
            html_str = html_str.replace("<head>", f"<head><base href='{base_url}'>")

    async with async_playwright() as p:
        browser = await p.chromium.launch(args=['--no-sandbox', '--disable-setuid-sandbox'])
        page = await browser.new_page()
        await page.set_content(html_str, wait_until="networkidle")
        pdf_bytes = await page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}
        )
        await browser.close()
        return pdf_bytes


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
