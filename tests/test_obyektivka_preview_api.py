"""Obyektivka preview API returns valid PDF bytes."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "templates" / "obyektivka_master.docx"


class TestObyektivkaPreviewApi(unittest.TestCase):
    def test_preview_returns_pdf_not_gzip(self):
        if not MASTER.is_file():
            self.skipTest("master docx missing")

        from fastapi.testclient import TestClient

        from backend.server_app import create_webhook_app

        app = create_webhook_app()
        client = TestClient(app)
        res = client.post(
            "/api/preview_obyektivka",
            json={
                "lang": "uz_lat",
                "fullname": "Test User",
                "birthdate": "01.01.1990",
                "nation": "O'zbek",
                "work_experience": [],
                "relatives": [],
                "watermark": True,
                "mask_pii": False,
            },
        )
        self.assertEqual(res.status_code, 200, res.text[:300])
        self.assertTrue(res.content[:4] == b"%PDF", res.content[:16])
        self.assertIn("application/pdf", res.headers.get("content-type", ""))
        enc = (res.headers.get("content-encoding") or "").lower()
        self.assertNotEqual(enc, "gzip")

    def test_preview_html_returns_document(self):
        from fastapi.testclient import TestClient

        from backend.server_app import create_webhook_app

        app = create_webhook_app()
        client = TestClient(app)
        res = client.post(
            "/api/preview_obyektivka_html",
            json={
                "lang": "uz_lat",
                "fullname": "Test User",
                "birthdate": "01.01.1990",
                "nation": "O'zbek",
                "work_experience": [],
                "relatives": [],
                "watermark": True,
                "mask_pii": False,
            },
        )
        self.assertEqual(res.status_code, 200, res.text[:300])
        self.assertIn("text/html", res.headers.get("content-type", ""))
        self.assertIn("Test User", res.text)
        self.assertIn("MEHNAT FAOLIYATI", res.text)


if __name__ == "__main__":
    unittest.main()
