"""Payment notification formatting."""
from __future__ import annotations

import unittest

from shared.payment_notifications import (
    build_payment_notification_text,
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


if __name__ == "__main__":
    unittest.main()
