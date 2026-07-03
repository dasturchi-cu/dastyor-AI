"""AI routing probe tests."""
from __future__ import annotations

import unittest

from features.ai.routing.probe import build_config_summary


class TestAiProbe(unittest.TestCase):
    def test_build_config_summary_shape(self):
        cfg = build_config_summary()
        self.assertIn("providers", cfg)
        self.assertIn("total_keys", cfg)
        self.assertIn("gemini", cfg["providers"])


if __name__ == "__main__":
    unittest.main()
