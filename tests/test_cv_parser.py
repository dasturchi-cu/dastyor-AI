import unittest


class TestCvParser(unittest.TestCase):
    def test_parse_sections(self):
        from backend.services.cv_parser import parse_cv_text

        txt = """
John Doe
Skills:
Python, FastAPI, PostgreSQL

Experience:
2022-2024 Backend Engineer - ACME
- Built APIs
"""
        r = parse_cv_text(txt)
        self.assertEqual(r.name, "John Doe")
        self.assertTrue(any("Python" == s for s in r.skills))
        self.assertTrue(len(r.experience) >= 1)


if __name__ == "__main__":
    unittest.main()

