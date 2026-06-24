"""Hozirgi ish (h.v.) ajratish va formatlash."""
from __future__ import annotations

import unittest

from features.obyektivka.current_job import extract_current_job, format_current_job_year, is_present_year_token


class TestCurrentJob(unittest.TestCase):
    def test_present_token(self):
        self.assertTrue(is_present_year_token("h.v"))
        self.assertTrue(is_present_year_token("hozirgacha"))
        self.assertFalse(is_present_year_token("2014"))

    def test_format_year_lat(self):
        self.assertEqual(format_current_job_year("2014", "uz_lat"), "2014-yildan:")

    def test_format_year_cyr(self):
        self.assertEqual(format_current_job_year("2014", "uz_cyr"), "2014 йилдан:")

    def test_format_year_with_day_lat(self):
        self.assertEqual(
            format_current_job_year("2007", "uz_lat", since="5 oktabr"),
            "2007 yil 5 oktabrdan:",
        )

    def test_format_year_with_day_cyr(self):
        self.assertEqual(
            format_current_job_year("2007", "uz_cyr", since="5 октябр"),
            "2007 йил 5 октябрдан:",
        )

    def test_extract_from_work_row(self):
        job, year, rest = extract_current_job(
            [{"f": "2014", "t": "h.v", "d": "MCHJ rahbari"}],
            lang="uz_lat",
        )
        self.assertEqual(job, "MCHJ rahbari")
        self.assertEqual(year, "2014-yildan:")
        self.assertEqual(len(rest), 1)
        self.assertIn("MCHJ rahbari", rest[0].get("position", ""))

    def test_extract_from_work_row_with_since(self):
        job, year, rest = extract_current_job(
            [{"f": "2007", "t": "h.v", "d": "MCHJ rahbari", "fs": "5 oktabr"}],
            lang="uz_lat",
        )
        self.assertEqual(job, "MCHJ rahbari")
        self.assertEqual(year, "2007 yil 5 oktabrdan:")
        self.assertEqual(len(rest), 1)

    def test_explicit_current_stays_in_works(self):
        job, year, rest = extract_current_job(
            [
                {"year": "2010-2013", "position": "Eski ish"},
                {"year": "2014-h.v.", "position": "Hozirgi ish"},
            ],
            current_job="Hozirgi ish",
            current_job_year="2014",
            lang="uz_lat",
        )
        self.assertEqual(job, "Hozirgi ish")
        self.assertEqual(year, "2014-yildan:")
        self.assertEqual(len(rest), 2)


if __name__ == "__main__":
    unittest.main()
