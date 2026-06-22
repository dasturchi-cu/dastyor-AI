"""CV data persistence repository."""
from __future__ import annotations

import json
from typing import Any

from database.connection import get_connection, row_to_dict
from database.repositories import users as users_repo


def _json_dump(val: Any) -> str | None:
    if val is None:
        return None
    if isinstance(val, str):
        return val
    return json.dumps(val, ensure_ascii=False)


def save(telegram_id: int, data: dict[str, Any]) -> dict[str, Any]:
    user = users_repo.upsert_user(telegram_id)
    uid = int(user["id"])
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO cv_data (
                user_id, full_name, phone, email, address, birth_date,
                education, experience, skills, languages, extra, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
                full_name = COALESCE(excluded.full_name, cv_data.full_name),
                phone = COALESCE(excluded.phone, cv_data.phone),
                email = COALESCE(excluded.email, cv_data.email),
                address = COALESCE(excluded.address, cv_data.address),
                birth_date = COALESCE(excluded.birth_date, cv_data.birth_date),
                education = COALESCE(excluded.education, cv_data.education),
                experience = COALESCE(excluded.experience, cv_data.experience),
                skills = COALESCE(excluded.skills, cv_data.skills),
                languages = COALESCE(excluded.languages, cv_data.languages),
                extra = COALESCE(excluded.extra, cv_data.extra),
                updated_at = datetime('now')
            """,
            (
                uid,
                data.get("full_name") or data.get("name"),
                data.get("phone"),
                data.get("email"),
                data.get("address") or data.get("loc"),
                data.get("birth_date") or data.get("birthdate"),
                _json_dump(data.get("education") or data.get("education_list")),
                _json_dump(data.get("experience") or data.get("works") or data.get("work_experience")),
                data.get("skills") if isinstance(data.get("skills"), str) else _json_dump(data.get("skills")),
                _json_dump(data.get("languages") or data.get("languages_list")),
                _json_dump({k: v for k, v in data.items() if k not in {
                    "full_name", "name", "phone", "email", "address", "loc",
                    "birth_date", "birthdate", "education", "education_list",
                    "experience", "works", "work_experience", "skills", "languages", "languages_list",
                }}),
            ),
        )
        row = conn.execute("SELECT * FROM cv_data WHERE user_id = ?", (uid,)).fetchone()
    return _to_form(row_to_dict(row) or {})


def get(telegram_id: int) -> dict[str, Any] | None:
    user = users_repo.get_by_telegram_id(telegram_id)
    if not user:
        return None
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM cv_data WHERE user_id = ?", (int(user["id"]),)).fetchone()
    if not row:
        return None
    return _to_form(row_to_dict(row) or {})


def _to_form(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if row.get("full_name"):
        out["name"] = row["full_name"]
    if row.get("phone"):
        out["phone"] = row["phone"]
    if row.get("email"):
        out["email"] = row["email"]
    if row.get("address"):
        out["loc"] = row["address"]
    if row.get("birth_date"):
        out["birthdate"] = row["birth_date"]
    for key in ("education", "experience", "languages", "extra"):
        raw = row.get(key)
        if not raw:
            continue
        try:
            out[key if key != "extra" else "_extra"] = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError:
            out[key] = raw
    if row.get("skills"):
        sk = row["skills"]
        try:
            parsed = json.loads(sk) if isinstance(sk, str) and sk.startswith("[") else sk
            out["skills"] = ", ".join(parsed) if isinstance(parsed, list) else parsed
        except json.JSONDecodeError:
            out["skills"] = sk
    if "_extra" in out and isinstance(out["_extra"], dict):
        out.update(out.pop("_extra"))
    return out
