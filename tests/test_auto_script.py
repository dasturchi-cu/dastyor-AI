import unittest


class TestAutoScript(unittest.TestCase):
    def test_latin_to_cyrillic(self):
        from backend.services.auto_script import auto_cyrillic_latin

        res = auto_cyrillic_latin("Assalomu alaykum")
        self.assertIn(res.direction, ("lotin_to_krill", "none"))
        self.assertTrue(isinstance(res.result, str))

    def test_cyrillic_to_latin(self):
        from backend.services.auto_script import auto_cyrillic_latin

        res = auto_cyrillic_latin("Ассалому алайкум")
        self.assertIn(res.direction, ("krill_to_lotin", "none"))
        self.assertTrue(isinstance(res.result, str))


if __name__ == "__main__":
    unittest.main()

