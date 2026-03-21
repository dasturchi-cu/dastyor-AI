"""Pydantic models for WebApp / public API (formerly inline in api_webhook)."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class AuthRequest(BaseModel):
    telegram_id: int
    first_name: str = ""
    username: str = ""
    photo_url: str = ""


class TranslitRequest(BaseModel):
    text: str
    direction: str


class NotifyRequest(BaseModel):
    telegram_id: int
    message: str
    token: Optional[str] = None


class SupportRequest(BaseModel):
    telegram_id: int
    username: Optional[str] = ""
    message: str
    token: Optional[str] = None


class TranslateRequest(BaseModel):
    text: str
    direction: str


class SpellcheckRequest(BaseModel):
    text: str


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
    deputy: str = ""
    address: str = ""
    phone: str = ""
    work_experience: list = []
    relatives: list = []
    photo_data: Optional[str] = None
    current_job: Optional[str] = None
    current_job_year: Optional[str] = None
    send_only: Optional[bool] = False


class ExportCVRequest(BaseModel):
    telegram_id: Optional[int] = None
    token: Optional[str] = None  # session from /api/auth (required for some deployments)
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


class ExportObyektivkaRequest(BaseModel):
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
    deputy: str = ""
    address: str = ""
    phone: str = ""
    work_experience: list = []
    relatives: list = []
    photo_data: Optional[str] = None
    current_job: Optional[str] = None
    current_job_year: Optional[str] = None
    send_only: Optional[bool] = False


class PreviewObyektivkaRequest(BaseModel):
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
    deputy: str = ""
    address: str = ""
    phone: str = ""
    work_experience: list = []
    relatives: list = []
