"""Payment notification formatting (O'zbek)."""
from __future__ import annotations

import unittest

from shared.payment_notifications import (
    build_daily_admin_report,
    build_payment_notification_text,
    build_returning_customer_alert,
    format_datetime_uz,
    format_username,
    payment_list_line,
    purchase_ordinal,
    purchase_ordinal_uz,
    split_datetime,
)


class TestPaymentNotifications(unittest.TestCase):
    def test_purchase_ordinal_uz(self):
        self.assertEqual(purchase_ordinal_uz(1), "1-chi xarid")
        self.assertEqual(purchase_ordinal_uz(5), "5-chi xarid")
        self.assertEqual(purchase_ordinal(5), "5-chi xarid")

    def test_format_username(self):
        self.assertEqual(format_username("johndoe"), "@johndoe")
        self.assertEqual(format_username(""), "Username yo'q")

    def test_split_datetime(self):
        # SQLite UTC → Toshkent (UTC+5)
        self.assertEqual(split_datetime("2026-06-22 21:35:10"), ("23.06.2026", "02:35"))
        self.assertEqual(format_datetime_uz("2026-06-24 07:06:00"), "24.06.2026, 12:06")

    def test_payment_list_line(self):
        line = payment_list_line(
            {
                "id": 154,
                "username": "johndoe",
                "first_name": "John",
                "payer_name": "John",
            }
        )
        self.assertIn("#154", line)
        self.assertIn("@johndoe", line)

    def test_build_notification_uz(self):
        text = build_payment_notification_text(
            {
                "id": 154,
                "telegram_id": 123456789,
                "username": "johndoe",
                "first_name": "John",
                "payer_name": "John",
                "document_type": "obyektivka",
                "created_at": "2026-06-22 21:35:00",
            },
            kind="obyektivka",
            purchase_number=5,
        )
        self.assertIn("YANGI TO'LOV #154", text)
        self.assertIn("5-chi xarid", text)
        self.assertIn("Obyektivka", text)
        self.assertIn("23.06.2026, 02:35", text)

    def test_build_daily_report_uz(self):
        text = build_daily_admin_report(
            {
                "new_users": 12,
                "cv": 8,
                "obyektivka": 5,
                "approved_payments": 7,
                "pending_payments": 3,
                "revenue_uzs": 55993,
                "conversion_pct": 15.0,
            },
            report_date="2026-06-22",
        )
        self.assertIn("Kunlik hisobot", text)
        self.assertIn("Konversiya", text)

    def test_returning_customer_uz(self):
        text = build_returning_customer_alert(
            {
                "id": 99,
                "telegram_id": 123,
                "username": "john",
                "first_name": "John",
                "payer_name": "John",
            },
            kind="cv",
            purchase_number=3,
            previous_approved=2,
        )
        self.assertIn("QAYTA MIJOZ", text)
        self.assertIn("3-chi xarid", text)


if __name__ == "__main__":
    unittest.main()
