"""Security and payment atomic tests."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

from core.telegram_auth import extract_telegram_user_id, validate_init_data
from database.connection import init_db
from database.repositories import payments as payments_repo
from database.repositories import users as users_repo


def _make_init_data(bot_token: str, user_id: int = 12345) -> str:
    user = json.dumps({"id": user_id, "first_name": "Test"}, separators=(",", ":"))
    pairs = {
        "auth_date": str(int(time.time())),
        "user": user,
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    digest = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    pairs["hash"] = digest
    return urlencode(pairs)


class TestTelegramAuth(unittest.TestCase):
    def test_valid_init_data(self):
        token = "123456:ABC-DEF"
        init_data = _make_init_data(token, 999)
        validated = validate_init_data(init_data, token)
        self.assertIsNotNone(validated)
        self.assertEqual(extract_telegram_user_id(validated), 999)

    def test_tampered_init_data(self):
        token = "123456:ABC-DEF"
        init_data = _make_init_data(token, 999) + "tamper"
        self.assertIsNone(validate_init_data(init_data, token))


class TestPaymentAtomic(unittest.TestCase):
    def setUp(self):
        init_db()

    def test_approve_atomic_grants_once(self):
        tid = 88001122
        users_repo.upsert_user(tid)
        users_repo.invalidate_cache(tid)
        before = users_repo.get_credits(tid)
        payment = payments_repo.create_payment(tid, payer_name="Test User")
        self.assertIsNotNone(payment)
        pid = int(payment["id"])

        first = payments_repo.approve_atomic(pid)
        self.assertIsNotNone(first)
        self.assertEqual(first["status"], "APPROVED")
        self.assertEqual(users_repo.get_credits(tid), before + 1)

        second = payments_repo.approve_atomic(pid)
        self.assertIsNotNone(second)
        self.assertEqual(users_repo.get_credits(tid), before + 1)

    def test_try_auto_approve_when_enabled(self):
        from features.payment import service as payment_service

        tid = 88003344
        users_repo.upsert_user(tid)
        payment = payments_repo.create_payment(tid, payer_name="Auto User")
        pid = int(payment["id"])
        before = users_repo.get_credits(tid)

        with patch("features.payment.service.settings") as mock_settings:
            mock_settings.auto_approve_payments = True
            result = payment_service.try_auto_approve(pid)
        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "APPROVED")
        self.assertEqual(users_repo.get_credits(tid), before + 1)

    def test_try_auto_approve_skipped_when_disabled(self):
        from features.payment import service as payment_service

        tid = 88005566
        payment = payments_repo.create_payment(tid, payer_name="Manual User")
        pid = int(payment["id"])
        before = users_repo.get_credits(tid)

        with patch("features.payment.service.settings") as mock_settings:
            mock_settings.auto_approve_payments = False
            result = payment_service.try_auto_approve(pid)
        self.assertIsNone(result)
        self.assertEqual(users_repo.get_credits(tid), before)

    def test_resolve_uid_from_init_data(self):
        from shared.auth import resolve_uid_from_webapp

        token = "123456:ABC-DEF"
        init_data = _make_init_data(token, 77112233)
        with patch("config.settings.settings") as mock_settings:
            mock_settings.bot_token = token
            mock_settings.init_data_max_age_seconds = 86_400
            uid = resolve_uid_from_webapp(77112233, token=None, init_data=init_data)
        self.assertEqual(uid, 77112233)

        with patch("config.settings.settings") as mock_settings:
            mock_settings.bot_token = token
            mock_settings.init_data_max_age_seconds = 86_400
            with patch("shared.auth.resolve_uid", return_value=None):
                uid_mismatch = resolve_uid_from_webapp(99999, token=None, init_data=init_data)
        self.assertIsNone(uid_mismatch)


if __name__ == "__main__":
    unittest.main()
