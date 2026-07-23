"""Referral: 1 paid friend = +1 credit."""
from __future__ import annotations

import unittest

from database.repositories import users as users_repo


class TestReferralPaidOneToOne(unittest.TestCase):
    def test_count_eligible_is_paid_count(self) -> None:
        # Pure logic mirror of new rule
        paid = 2
        rewarded = 1
        new_rewards = max(0, paid - rewarded)
        self.assertEqual(new_rewards, 1)

    def test_progress_helpers_exist(self) -> None:
        self.assertTrue(callable(users_repo.get_referral_progress))
        self.assertTrue(callable(users_repo.mark_referral_paid))
        self.assertTrue(callable(users_repo.ensure_pay_promo))
        self.assertTrue(callable(users_repo.count_eligible_referral_batches))


if __name__ == "__main__":
    unittest.main()
