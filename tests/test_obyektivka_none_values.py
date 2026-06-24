"""yo'q / йўқ normalizatsiya."""
from __future__ import annotations

import unittest

from features.obyektivka.none_values import field_or_none, is_none_token


class TestNoneValues(unittest.TestCase):
    def test_yoq_is_none(self):
        self.assertTrue(is_none_token("yo'q"))
        self.assertTrue(is_none_token("йўқ"))

    def test_cyrillic_none_for_spec(self):
        self.assertEqual(field_or_none("yo'q", "uz_cyr"), "йўқ")
        self.assertEqual(field_or_none("йўқ", "uz_lat"), "yo'q")

    def test_real_value_unchanged(self):
        self.assertEqual(field_or_none("iqtisodchi", "uz_cyr"), "iqtisodchi")


if __name__ == "__main__":
    unittest.main()
