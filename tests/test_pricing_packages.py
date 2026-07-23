"""Credit packages + simplified referral + signup demo-only."""
from __future__ import annotations

import unittest

from shared.pricing import get_package, list_packages, soft_paywall_text
from shared.keyboards import referral_share_button


class TestPricingPackages(unittest.TestCase):
    def test_three_packages(self) -> None:
        packs = list_packages()
        self.assertEqual(len(packs), 3)
        self.assertEqual(packs[0]["credits"], 1)
        self.assertEqual(packs[0]["price_uzs"], 7999)
        self.assertEqual(packs[1]["credits"], 3)
        self.assertEqual(packs[1]["price_uzs"], 14999)
        self.assertEqual(packs[2]["credits"], 5)
        self.assertEqual(packs[2]["price_uzs"], 19999)

    def test_get_package_default(self) -> None:
        self.assertEqual(get_package(None).id, "pack1")
        self.assertEqual(get_package("pack5").credits, 5)

    def test_soft_paywall_mentions_demo(self) -> None:
        text = soft_paywall_text(promo_active=True, promo_hours_left=20)
        self.assertIn("Demo", text)
        self.assertIn("Muqova", text)
        self.assertIn("3×", text)


class TestReferralShareCopy(unittest.TestCase):
    def test_share_mentions_paid_friend(self) -> None:
        btn = referral_share_button(42)
        self.assertIn("to'lasa", btn.text.lower().replace("ʻ", "'").replace("'", "'") or btn.text)
        self.assertIn("ref_42", btn.url or "")


if __name__ == "__main__":
    unittest.main()
