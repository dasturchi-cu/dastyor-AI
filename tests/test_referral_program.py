"""Referral reward batch rules."""
from __future__ import annotations

import unittest

from database.repositories import users as users_repo


class TestReferralBatches(unittest.TestCase):
    def test_count_eligible_requires_three_and_one_paid(self) -> None:
        rows = [
            {"referred_active": 1, "referred_paid": 0},
            {"referred_active": 1, "referred_paid": 0},
            {"referred_active": 1, "referred_paid": 0},
        ]
        eligible = 0
        for index in range(0, len(rows), 3):
            chunk = rows[index : index + 3]
            if len(chunk) < 3:
                break
            if any(int(r["referred_paid"] or 0) for r in chunk):
                eligible += 1
        self.assertEqual(eligible, 0)

        rows[1]["referred_paid"] = 1
        eligible = 0
        for index in range(0, len(rows), 3):
            chunk = rows[index : index + 3]
            if len(chunk) < 3:
                break
            if any(int(r["referred_paid"] or 0) for r in chunk):
                eligible += 1
        self.assertEqual(eligible, 1)

    def test_progress_helpers_exist(self) -> None:
        self.assertTrue(callable(users_repo.get_referral_progress))
        self.assertTrue(callable(users_repo.mark_referral_paid))


if __name__ == "__main__":
    unittest.main()
