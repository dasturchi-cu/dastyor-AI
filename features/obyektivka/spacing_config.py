"""Obyektivka vertikal masofalar — .env orqali (namuna PPT bilan mos)."""

from __future__ import annotations

import os


def _float_env(name: str, default: float) -> float:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# HTML preview / PDF / HTML→DOCX (mm)
HDR_TITLE_NAME_GAP_MM = _float_env("OBY_HDR_TITLE_NAME_GAP_MM", 1.5)
HDR_BLOCK_MIN_HEIGHT_MM = _float_env("OBY_HDR_BLOCK_MIN_HEIGHT_MM", 28.0)
HDR_NAME_BOTTOM_MM = _float_env("OBY_HDR_NAME_BOTTOM_MM", 0.5)
FIELD_ROW_GAP_MM = _float_env("OBY_FIELD_ROW_GAP_MM", 1.8)
CURRENT_JOB_BOTTOM_MM = _float_env("OBY_CURRENT_JOB_BOTTOM_MM", 2.0)
SECTION_WORK_MARGIN_TOP_MM = _float_env("OBY_SECTION_WORK_MARGIN_TOP_MM", 1.2)
SECTION_WORK_MARGIN_BOTTOM_MM = _float_env("OBY_SECTION_WORK_MARGIN_BOTTOM_MM", 1.0)
WORK_ITEM_GAP_MM = _float_env("OBY_WORK_ITEM_GAP_MM", 0.8)
REL_TITLE_GAP_MM = _float_env("OBY_REL_TITLE_GAP_MM", 3.0)

# Master DOCX zaxira (twips, 1/20 pt)
DOCX_AFTER_FISH_TWIPS = _int_env("OBY_DOCX_AFTER_FISH_TWIPS", 200)
DOCX_GRID_BEFORE_TWIPS = _int_env("OBY_DOCX_GRID_BEFORE_TWIPS", 160)
DOCX_CURRENT_JOB_BEFORE_TWIPS = _int_env("OBY_DOCX_CURRENT_JOB_BEFORE_TWIPS", 160)
DOCX_CURRENT_JOB_AFTER_TWIPS = _int_env("OBY_DOCX_CURRENT_JOB_AFTER_TWIPS", 0)
DOCX_MEHNAT_BEFORE_TWIPS = _int_env("OBY_DOCX_MEHNAT_BEFORE_TWIPS", 80)
DOCX_TITLE_AFTER_TWIPS = _int_env("OBY_DOCX_TITLE_AFTER_TWIPS", 120)

# Shriftlar (pt) — namuna PPT
FONT_TITLE_PT = _float_env("OBY_FONT_TITLE_PT", 14.0)
FONT_BODY_PT = _float_env("OBY_FONT_BODY_PT", 11.0)
FONT_REL_TITLE_PT = _float_env("OBY_FONT_REL_TITLE_PT", 12.0)


def html_layout_css_vars() -> dict[str, str]:
    """Jinja/CSS uchun layout kalitlari."""
    return {
        "hdr_title_name_gap_mm": f"{HDR_TITLE_NAME_GAP_MM:g}",
        "hdr_block_min_height_mm": f"{HDR_BLOCK_MIN_HEIGHT_MM:g}",
        "hdr_name_bottom_mm": f"{HDR_NAME_BOTTOM_MM:g}",
        "field_row_gap_mm": f"{FIELD_ROW_GAP_MM:g}",
        "current_job_bottom_mm": f"{CURRENT_JOB_BOTTOM_MM:g}",
        "section_work_margin_top_mm": f"{SECTION_WORK_MARGIN_TOP_MM:g}",
        "section_work_margin_bottom_mm": f"{SECTION_WORK_MARGIN_BOTTOM_MM:g}",
        "work_item_gap_mm": f"{WORK_ITEM_GAP_MM:g}",
        "rel_title_gap_mm": f"{REL_TITLE_GAP_MM:g}",
        "font_title_pt": f"{FONT_TITLE_PT:g}",
        "font_body_pt": f"{FONT_BODY_PT:g}",
        "font_rel_title_pt": f"{FONT_REL_TITLE_PT:g}",
    }
