"""Hozirgi ish (h.v.) — orqaga moslik qatlami."""
from __future__ import annotations

from typing import Any

from features.obyektivka.malumotnoma_data import (
    build_malumotnoma_data,
    format_current_job_year,
    is_present_year_token,
)

__all__ = [
    "build_malumotnoma_data",
    "extract_current_job",
    "format_current_job_year",
    "is_present_year_token",
]


def extract_current_job(
    work_items: list[dict[str, Any]],
    *,
    current_job: str = "",
    current_job_year: str = "",
    lang: str = "uz_lat",
) -> tuple[str, str, list[dict[str, Any]]]:
    """H.v. ish + to'liq mehnat ro'yxati (olib tashlanmaydi)."""
    data = build_malumotnoma_data(
        {
            "lang": lang,
            "current_job": current_job,
            "current_job_year": current_job_year,
            "work_experience": work_items,
        }
    )
    return data["current_job"], data["current_job_year"], data["work_experience"]
