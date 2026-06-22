"""Full-stack smoke test — run before deploy."""
from __future__ import annotations

import os

# Local smoke: production auth requires initData; enable dev fallback for tests only.
os.environ.setdefault("ALLOW_INSECURE_AUTH", "1")
os.environ.setdefault("USE_REDIS", "0")

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"
TID = 999888777


def _post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def _get(path: str) -> dict:
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return json.loads(r.read())


def main() -> int:
    errors: list[str] = []

    def check(name: str, fn):
        try:
            fn()
            print(f"OK  {name}")
        except Exception as e:
            errors.append(f"{name}: {e}")
            print(f"FAIL {name}: {e}")

    check("health", lambda: _get("/health"))
    check("payment_card", lambda: _get("/api/payment_card"))

    token_holder: dict = {}

    def auth():
        r = _post("/api/auth", {"telegram_id": TID, "first_name": "Smoke", "username": "smoke"})
        assert r.get("ok"), r
        token_holder["token"] = r["token"]

    check("auth", auth)
    token = token_holder.get("token", "")

    from database.connection import init_db
    from database.repositories import users as users_repo

    init_db()
    users_repo.upsert_user(TID)
    users_repo.add_credits(TID, 5)

    check("me", lambda: _get(f"/api/me?telegram_id={TID}&token={token}"))
    check("stats", lambda: _get(f"/api/stats?telegram_id={TID}&token={token}"))
    check(
        "translit",
        lambda: _post(
            "/api/translit",
            {"text": "Assalomu alaykum", "telegram_id": TID, "token": token},
        ),
    )

    def cv_preview():
        req = urllib.request.Request(
            BASE + "/api/cv_preview_html",
            data=json.dumps(
                {"name": "Smoke Test", "phone": "+998901234567", "telegram_id": TID, "token": token}
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            html = r.read()
            assert len(html) > 1000, len(html)

    check("cv_preview", cv_preview)

    def cv_export():
        req = urllib.request.Request(
            BASE + "/api/export_cv",
            data=json.dumps(
                {
                    "name": "Smoke Test",
                    "phone": "+998901234567",
                    "email": "smoke@test.com",
                    "loc": "Toshkent",
                    "spec": "Dev",
                    "skills": "Python",
                    "works": [{"title": "Dev", "company": "IT", "from": "2020", "to": "2024"}],
                    "education_list": [{"title": "CS", "company": "TDIU", "date": "2016-2020"}],
                    "telegram_id": TID,
                    "token": token,
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
            assert data[:4] == b"%PDF", data[:20]

    check("cv_export_pdf", cv_export)

    def oby_export():
        req = urllib.request.Request(
            BASE + "/api/export_obyektivka",
            data=json.dumps(
                {
                    "fullname": "Smoke Test",
                    "birthdate": "01.01.1990",
                    "birthplace": "Toshkent",
                    "nation": "ozbek",
                    "education": "oliy",
                    "graduated": "TDIU",
                    "specialty": "IT",
                    "party": "yoq",
                    "degree": "yoq",
                    "scientific_title": "yoq",
                    "languages": "rus",
                    "awards": "yoq",
                    "deputy": "yoq",
                    "work_experience": [{"year": "2012-2020", "position": "Dev"}],
                    "relatives": [
                        {
                            "degree": "ota",
                            "fullname": "Test",
                            "birth_year_place": "1960",
                            "work_place": "x",
                            "address": "Toshkent",
                        }
                    ],
                    "telegram_id": TID,
                    "token": token,
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
            assert data[:2] == b"PK", data[:20]

    check("oby_export_docx", oby_export)

    def oby_preview():
        req = urllib.request.Request(
            BASE + "/api/preview_obyektivka",
            data=json.dumps(
                {
                    "fullname": "Smoke Test",
                    "birthdate": "01.01.1990",
                    "birthplace": "Toshkent",
                    "nation": "ozbek",
                    "education": "oliy",
                    "graduated": "TDIU",
                    "specialty": "IT",
                    "party": "yoq",
                    "degree": "yoq",
                    "scientific_title": "yoq",
                    "languages": "rus",
                    "awards": "yoq",
                    "deputy": "yoq",
                    "work_experience": [{"year": "2012-2020", "position": "Dev"}],
                    "relatives": [],
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
            assert data[:4] == b"%PDF", data[:20]
            assert len(data) > 1000, len(data)

    check("oby_preview_pdf", oby_preview)

    async def ai_text():
        from features.ai.service import process_text_for_cv

        _, data, _ = await process_text_for_cv(
            "Men Smoke Testman, Toshkent, telefon 998901234567, Python dasturchiman"
        )
        assert data.get("name") or data.get("phone"), data

    check("gemini_cv_text", lambda: asyncio.run(ai_text()))

    if errors:
        print("\n=== SMOKE TEST FAILED ===")
        for e in errors:
            print(" -", e)
        return 1
    print("\n=== ALL SMOKE TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
