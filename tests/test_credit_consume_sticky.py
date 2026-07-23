"""Credit consume must stick after successful export (no false refund)."""
from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from database.connection import get_connection, init_db
from database.repositories import users as users_repo
from features.cv import service as cv_service
from features.obyektivka import service as oby_service


class TestCreditConsumeSticky(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        init_db()

    def _reset(self, tid: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM payments WHERE user_id IN (SELECT id FROM users WHERE telegram_id = ?)",
                (tid,),
            )
            conn.execute("DELETE FROM users WHERE telegram_id = ?", (tid,))
            conn.commit()
        users_repo.upsert_user(tid, first_name="Consume")
        users_repo.add_credits(tid, 1)

    async def test_cv_export_consumes_even_if_referral_fails(self) -> None:
        tid = 880022001
        self._reset(tid)
        self.assertEqual(users_repo.get_credits(tid), 1)

        async def _boom(*_a, **_k):
            raise RuntimeError("notify fail")

        with patch("features.cv.service.generate_cv_pdf", new=AsyncMock(return_value=b"%PDF-1.4 ok")), patch(
            "features.cv.service._export_pdf_sync", return_value=(b"%PDF-1.4 ok", "x.pdf")
        ), patch(
            "database.repositories.users.activate_referral", side_effect=_boom
        ):
            # activate_referral is called via async_db.run — patch users_repo path used in service
            with patch("features.cv.service.users_repo.activate_referral", side_effect=RuntimeError("ref")):
                pdf, name = await cv_service.export_pdf(tid, {"name": "Test"}, bot=object())
                self.assertTrue(pdf)
                self.assertTrue(name)

        self.assertEqual(users_repo.get_credits(tid), 0)

    async def test_oby_export_consumes_even_if_referral_fails(self) -> None:
        tid = 880022002
        self._reset(tid)
        self.assertEqual(users_repo.get_credits(tid), 1)

        with patch(
            "features.obyektivka.service._export_docx_sync",
            return_value=(b"PKdocx", "x.docx"),
        ), patch(
            "features.obyektivka.service.users_repo.activate_referral",
            side_effect=RuntimeError("ref"),
        ):
            data, name = await oby_service.export_docx(tid, {"fullname": "Test"}, bot=object())
            self.assertTrue(data)
            self.assertTrue(name)

        self.assertEqual(users_repo.get_credits(tid), 0)

    async def test_failed_generate_refunds_once(self) -> None:
        tid = 880022003
        self._reset(tid)
        with patch("features.cv.service.generate_cv_pdf", new=AsyncMock(return_value=b"")):
            with self.assertRaises(RuntimeError):
                await cv_service.export_pdf(tid, {"name": "Test"}, bot=None)
        self.assertEqual(users_repo.get_credits(tid), 1)


if __name__ == "__main__":
    unittest.main()
