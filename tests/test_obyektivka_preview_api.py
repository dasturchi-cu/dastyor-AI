"""Obyektivka preview API returns valid PDF bytes from master DOCX."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "templates" / "obyektivka_master.docx"


class TestObyektivkaPreviewApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from fastapi.testclient import TestClient

        from backend.server_app import create_webhook_app

        cls.client = TestClient(create_webhook_app())

    def test_preview_returns_pdf_not_gzip(self):
        if not MASTER.is_file():
            self.skipTest("master docx missing")

        fake_pdf = b"%PDF-1.4\n" + (b"0" * 120)
        with patch(
            "features.obyektivka.router._build_oby_docx_pdf",
            new_callable=AsyncMock,
            return_value=fake_pdf,
        ) as docx_pdf:
            res = self.client.post(
                "/api/preview_obyektivka",
                json={
                    "telegram_id": 88001122,
                    "lang": "uz_lat",
                    "fullname": "Test User",
                    "birthdate": "01.01.1990",
                    "nation": "O'zbek",
                    "work_experience": [],
                    "relatives": [],
                    "watermark": False,
                    "mask_pii": False,
                },
            )
        self.assertEqual(res.status_code, 200, res.text[:300])
        self.assertEqual(res.content, fake_pdf)
        docx_pdf.assert_awaited_once()
        self.assertFalse(docx_pdf.await_args.kwargs.get("watermark"))

    def test_preview_html_endpoint_returns_docx_pdf(self):
        fake_pdf = b"%PDF-1.4\n" + (b"0" * 120)
        with patch(
            "features.obyektivka.router._build_oby_preview_pdf",
            new_callable=AsyncMock,
            return_value=fake_pdf,
        ) as preview_pdf:
            res = self.client.post(
                "/api/preview_obyektivka_html",
                json={
                    "telegram_id": 88001122,
                    "lang": "uz_lat",
                    "fullname": "Test User",
                    "birthdate": "01.01.1990",
                    "nation": "O'zbek",
                    "work_experience": [],
                    "relatives": [],
                },
            )
        self.assertEqual(res.status_code, 200, res.text[:300])
        self.assertEqual(res.content, fake_pdf)
        self.assertIn("application/pdf", res.headers.get("content-type", ""))
        preview_pdf.assert_awaited_once()

    def test_demo_pdf_uses_docx_watermark_pipeline(self):
        fake_pdf = b"%PDF-1.4\n" + (b"0" * 120)
        with patch(
            "features.obyektivka.router._build_oby_docx_pdf",
            new_callable=AsyncMock,
            return_value=fake_pdf,
        ) as docx_pdf:
            res = self.client.post(
                "/api/test_obyektivka_pdf",
                json={
                    "telegram_id": 88001122,
                    "lang": "uz_lat",
                    "fullname": "Test User",
                    "birthdate": "01.01.1990",
                    "nation": "O'zbek",
                    "work_experience": [],
                    "relatives": [],
                    "send_to_bot": False,
                },
            )
        self.assertEqual(res.status_code, 200, res.text[:300])
        self.assertEqual(res.content, fake_pdf)
        docx_pdf.assert_awaited_once()
        self.assertTrue(docx_pdf.await_args.kwargs.get("watermark"))


if __name__ == "__main__":
    unittest.main()
