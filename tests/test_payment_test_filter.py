"""Test payment filter — audit/smoke users admin kanaliga ketmasin."""
from __future__ import annotations

import unittest

from shared.payment_test_filter import is_test_payment


class TestPaymentTestFilter(unittest.TestCase):
    def test_manual_user_is_test(self):
        self.assertTrue(
            is_test_payment(
                {
                    "telegram_id": 88005566,
                    "payer_name": "Manual User",
                    "username": "",
                }
            )
        )

    def test_smoke_user_is_test(self):
        self.assertTrue(
            is_test_payment(
                {
                    "telegram_id": 999888777,
                    "first_name": "Smoke",
                    "username": "smoke",
                }
            )
        )

    def test_auto_user_is_test(self):
        self.assertTrue(
            is_test_payment(
                {
                    "telegram_id": 88003344,
                    "payer_name": "Auto User",
                    "username": "",
                }
            )
        )

    def test_atomic_test_id_is_test(self):
        self.assertTrue(
            is_test_payment(
                {
                    "telegram_id": 88001122,
                    "payer_name": "Test User",
                }
            )
        )

    def test_real_user_not_test(self):
        self.assertFalse(
            is_test_payment(
                {
                    "telegram_id": 7458702074,
                    "first_name": "Botir",
                    "username": "real_user",
                    "payer_name": "Eshmatov Botir",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
