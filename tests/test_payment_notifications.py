"""Payment notification formatting."""
from __future__ import annotations

import unittest

from shared.payment_notifications import (
    build_daily_admin_report,
    build_payment_notification_text,
    build_returning_customer_alert,
    format_username,
    payment_list_line,
    purchase_ordinal,
    split_datetime,
)


class TestPaymentNotifications(unittest.TestCase):
    def test_purchase_ordinal(self):
        self.assertEqual(purchase_ordinal(1), "1st purchase")
        self.assertEqual(purchase_ordinal(2), "2nd purchase")
        self.assertEqual(purchase_ordinal(3), "3rd purchase")
        self.assertEqual(purchase_ordinal(4), "4th purchase")
        self.assertEqual(purchase_ordinal(5), "5th purchase")
        self.assertEqual(purchase_ordinal(10), "10th purchase")
        self.assertEqual(purchase_ordinal(11), "11th purchase")
        self.assertEqual(purchase_ordinal(21), "21st purchase")
        self.assertEqual(purchase_ordinal(22), "22nd purchase")
        self.assertEqual(purchase_ordinal(27), "27th purchase")

    def test_format_username(self):
        self.assertEqual(format_username("johndoe"), "@johndoe")
        self.assertEqual(format_username("@johndoe"), "@johndoe")
        self.assertEqual(format_username(""), "No Username")
        self.assertEqual(format_username(None), "No Username")

    def test_split_datetime(self):
        self.assertEqual(split_datetime("2026-06-22 21:35:10"), ("2026-06-22", "21:35"))
        self.assertEqual(split_datetime("2026-06-22T21:35:10"), ("2026-06-22", "21:35"))

    def test_payment_list_line(self):
        line = payment_list_line(
            {
                "id": 154,
                "username": "johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "payer_name": "John Doe",
            }
        )
        self.assertIn("#154", line)
        self.assertIn("@johndoe", line)
        self.assertIn("John Doe", line)

    def test_build_notification_includes_profile_link(self):
        text = build_payment_notification_text(
            {
                "id": 154,
                "telegram_id": 123456789,
                "username": "johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "payer_name": "John Doe",
                "document_type": "obyektivka",
                "created_at": "2026-06-22 21:35:00",
            },
            kind="obyektivka",
            purchase_number=5,
        )
        self.assertIn("tg://user?id=123456789", text)
        self.assertIn("5th purchase", text)
        self.assertIn("Obyektivka", text)

    def test_build_notification_no_username(self):
        text = build_payment_notification_text(
            {
                "id": 1,
                "telegram_id": 1,
                "payer_name": "X",
                "created_at": "2026-01-01 00:00:00",
            },
            kind="cv",
            purchase_number=1,
        )
        self.assertIn("No Username", text)

    def test_build_daily_report(self):
        text = build_daily_admin_report(
            {
                "new_users": 12,
                "active_users": 45,
                "cv": 8,
                "obyektivka": 5,
                "approved_payments": 7,
                "pending_payments": 3,
                "revenue_uzs": 55993,
            },
            report_date="2026-06-22",
        )
        self.assertIn("New Users", text)
        self.assertIn("Active Users", text)
        self.assertIn("Pending Payments", text)
        self.assertIn("55,993 UZS", text)

    def test_returning_customer_alert(self):
        text = build_returning_customer_alert(
            {
                "id": 99,
                "telegram_id": 123,
                "username": "john",
                "first_name": "John",
                "payer_name": "John",
                "document_type": "cv",
            },
            kind="cv",
            purchase_number=3,
            previous_approved=2,
        )
        self.assertIn("RETURNING CUSTOMER", text)
        self.assertIn("3rd purchase", text)
        self.assertIn("Previous approved", text)


if __name__ == "__main__":
    unittest.main()
