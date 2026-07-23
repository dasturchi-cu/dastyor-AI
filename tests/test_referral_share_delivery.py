"""Referral share helpers on document delivery."""
from __future__ import annotations

import unittest

from shared.keyboards import (
    document_ready_share_note,
    payment_choice_keyboard,
    referral_link,
    referral_share_button,
    referral_share_keyboard,
)


class TestReferralShareOnDocuments(unittest.TestCase):
    def test_referral_link(self) -> None:
        link = referral_link(12345)
        self.assertIn("start=ref_12345", link)
        self.assertTrue(link.startswith("https://t.me/"))

    def test_share_button(self) -> None:
        btn = referral_share_button(99)
        self.assertIn("+1", btn.text)
        self.assertIn("share/url", btn.url or "")
        self.assertIn("ref_99", btn.url or "")

    def test_payment_keyboard_has_packages(self) -> None:
        kb = payment_choice_keyboard(7)
        callbacks = [b.callback_data or "" for row in kb.inline_keyboard for b in row]
        self.assertTrue(any(c.startswith("pay_pack_") for c in callbacks))

    def test_ready_note_mentions_reward(self) -> None:
        note = document_ready_share_note()
        self.assertIn("+1", note)

    def test_share_keyboard_shape(self) -> None:
        kb = referral_share_keyboard(1)
        self.assertEqual(len(kb.inline_keyboard), 1)
        self.assertEqual(len(kb.inline_keyboard[0]), 1)


if __name__ == "__main__":
    unittest.main()
