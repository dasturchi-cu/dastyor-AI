"""Pydantic models for WebApp / public API (formerly inline in api_webhook)."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


class AuthRequest(BaseModel):
    telegram_id: int
    first_name: str = ""
    username: str = ""
    photo_url: str = ""
    init_data: str = ""
    turnstile_token: str = ""


class TranslitRequest(BaseModel):
    text: str
    direction: str = "auto"
    telegram_id: Optional[int] = None
    token: Optional[str] = None


class NotifyRequest(BaseModel):
    telegram_id: int
    message: str
    token: Optional[str] = None


def _coerce_oby_work_aliases(data: Any) -> Any:
    if not isinstance(data, dict):
        return data
    out = dict(data)
    if not out.get("work_experience"):
        for key in ("works", "employment_history", "employmentHistory", "work_history", "workHistory"):
            items = out.get(key)
            if items:
                out["work_experience"] = items
                break
    works = out.get("work_experience")
    if isinstance(works, list):
        norm: list[dict[str, Any]] = []
        for item in works:
            if not isinstance(item, dict):
                continue
            f = str(item.get("from") or item.get("f") or "").strip()
            t = str(item.get("to") or item.get("t") or "").strip()
            fs = str(
                item.get("from_since") or item.get("fs") or item.get("since") or ""
            ).strip()
            pos = str(
                item.get("position")
                or item.get("d")
                or item.get("desc")
                or item.get("description")
                or ""
            ).strip()
            year = str(item.get("year") or item.get("period") or "").strip()
            if not year and (f or t):
                if f and t:
                    year = f"{f}-{t}"
                else:
                    year = f or t
            row: dict[str, Any] = {"year": year, "position": pos}
            if f:
                row["from"] = f
                row["f"] = f
            if t:
                row["to"] = t
                row["t"] = t
            if fs:
                row["from_since"] = fs
                row["fs"] = fs
            norm.append(row)
        out["work_experience"] = norm
    if not out.get("current_job"):
        for key in ("currentJob", "current_position", "current_employment", "currentEmployment"):
            val = out.get(key)
            if val:
                out["current_job"] = val
                break
    if not out.get("current_job_year") and out.get("currentJobYear"):
        out["current_job_year"] = out["currentJobYear"]
    return out


class SupportRequest(BaseModel):
    telegram_id: int
    username: Optional[str] = ""
    message: str
    token: Optional[str] = None


class TranslateRequest(BaseModel):
    text: str
    direction: str
    telegram_id: Optional[int] = None
    token: Optional[str] = None


class TranslateAutoRequest(BaseModel):
    text: str
    target_lang: str = Field(..., description="uz|ru|en")
    telegram_id: Optional[int] = None
    token: Optional[str] = None


class SpellcheckRequest(BaseModel):
    text: str
    telegram_id: Optional[int] = None
    token: Optional[str] = None


class ObjectiveRequest(BaseModel):
    role: str = ""
    experience: str = "junior"
    extra: str = ""
    lang: str = "uz"


class CVRequest(BaseModel):
    telegram_id: Optional[int] = None
    token: Optional[str] = None  # session from /api/auth
    name: str = ""
    spec: str = ""
    phone: str = ""
    email: str = ""
    loc: str = ""
    addr: str = ""
    birth: str = ""
    place: str = ""
    nation: str = ""
    langs: str = ""
    about: str = ""
    template: str = "minimal"
    works: list = []
    education_list: list = []
    skills: str = ""
    languages_list: list = Field(default_factory=list)
    achievements_list: list = Field(default_factory=list)
    accent_color: str = "#3b82f6"
    img: str = ""


class ObyektivkaRequest(BaseModel):
    telegram_id: Optional[int] = None
    token: Optional[str] = None
    format: str = "word"
    lang: str = "uz_lat"
    fullname: str = ""
    birthdate: str = ""
    birthplace: str = ""
    nation: str = ""
    party: str = ""
    education: str = ""
    graduated: str = ""
    specialty: str = ""
    degree: str = ""
    scientific_title: str = ""
    languages: str = ""
    military_rank: str = ""
    awards: str = ""
    departmental_awards: str = ""
    deputy: str = ""
    address: str = ""
    phone: str = ""
    work_experience: list = []
    relatives: list = []
    photo_data: Optional[str] = None
    current_job: Optional[str] = None
    current_job_year: Optional[str] = None
    send_only: Optional[bool] = False

    @model_validator(mode="before")
    @classmethod
    def _coerce_aliases(cls, data: Any) -> Any:
        return _coerce_oby_work_aliases(data)


class ExportCVRequest(BaseModel):
    telegram_id: Optional[int] = None
    token: Optional[str] = None  # session from /api/auth (required for some deployments)
    init_data: Optional[str] = None  # Telegram WebApp initData fallback
    format: str = "pdf"
    lang: str = "uz_lat"
    send_only: Optional[bool] = False
    name: str = ""
    spec: str = ""
    phone: str = ""
    email: str = ""
    loc: str = ""
    addr: str = ""
    birth: str = ""
    place: str = ""
    nation: str = ""
    langs: str = ""
    about: str = ""
    template: str = "minimal"
    works: list = []
    education_list: list = []
    skills: str = ""
    img: str = ""
    languages_list: list = Field(default_factory=list)
    achievements_list: list = Field(default_factory=list)
    accent_color: str = "#3b82f6"


class ExportObyektivkaRequest(BaseModel):
    telegram_id: Optional[int] = None
    token: Optional[str] = None
    init_data: Optional[str] = None
    format: str = "word"
    lang: str = "uz_lat"
    fullname: str = ""
    birthdate: str = ""
    birthplace: str = ""
    nation: str = ""
    party: str = ""
    education: str = ""
    graduated: str = ""
    specialty: str = ""
    degree: str = ""
    scientific_title: str = ""
    languages: str = ""
    military_rank: str = ""
    awards: str = ""
    departmental_awards: str = ""
    deputy: str = ""
    address: str = ""
    phone: str = ""
    work_experience: list = []
    relatives: list = []
    photo_data: Optional[str] = None
    current_job: Optional[str] = None
    current_job_year: Optional[str] = None
    send_only: Optional[bool] = False

    @model_validator(mode="before")
    @classmethod
    def _coerce_aliases(cls, data: Any) -> Any:
        return _coerce_oby_work_aliases(data)


class PreviewObyektivkaRequest(BaseModel):
    telegram_id: Optional[int] = None
    token: Optional[str] = None
    init_data: Optional[str] = None
    lang: str = "uz_lat"
    fullname: str = ""
    birthdate: str = ""
    birthplace: str = ""
    nation: str = ""
    party: str = ""
    education: str = ""
    graduated: str = ""
    specialty: str = ""
    degree: str = ""
    scientific_title: str = ""
    languages: str = ""
    military_rank: str = ""
    awards: str = ""
    departmental_awards: str = ""
    deputy: str = ""
    address: str = ""
    phone: str = ""
    work_experience: list = []
    relatives: list = []
    photo_data: Optional[str] = None
    current_job: Optional[str] = None
    current_job_year: Optional[str] = None
    watermark: bool = True
    mask_pii: bool = False

    @model_validator(mode="before")
    @classmethod
    def _coerce_aliases(cls, data: Any) -> Any:
        return _coerce_oby_work_aliases(data)


class TestObyektivkaPdfRequest(PreviewObyektivkaRequest):
    telegram_id: Optional[int] = None
    token: Optional[str] = None
    init_data: Optional[str] = None
    send_to_bot: bool = True
