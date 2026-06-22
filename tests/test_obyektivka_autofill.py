"""Obyektivka AI autofill — h.v. va ish yillari normalizatsiyasi."""
from __future__ import annotations

import unittest

from features.ai.service import map_obyektivka_fields


class TestObyektivkaAutofill(unittest.TestCase):
    def test_splits_current_job_hv(self):
        data = map_obyektivka_fields(
            {
                "fullname": "Test User",
                "work_experience": [
                    {"year": "1977-1982", "position": "Talaba"},
                    {"year": "2007-h.v.", "position": "Rahbar"},
                ],
            }
        )
        self.assertEqual(data.get("current_job"), "Rahbar")
        self.assertIn("2007", str(data.get("current_job_year") or ""))
        years = [w["year"] for w in data.get("work_experience") or []]
        self.assertEqual(years, ["1977-1982 yy."])

    def test_normalizes_year_ranges(self):
        data = map_obyektivka_fields(
            {
                "fullname": "Test",
                "work_experience": [{"year": "1988-1991", "position": "Aspirant"}],
            }
        )
        self.assertEqual(data["work_experience"][0]["year"], "1988-1991 yy.")


if __name__ == "__main__":
    unittest.main()
