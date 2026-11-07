"""Every Python module must import — a syntax error anywhere takes the bot down at startup."""
from __future__ import annotations

import ast
import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class TestAppImports(unittest.TestCase):
    def test_all_tracked_python_files_parse(self):
        files = subprocess.run(
            ["git", "ls-files", "*.py"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.split()
        self.assertTrue(files)
        errors = []
        for rel in files:
            try:
                ast.parse((ROOT / rel).read_text(encoding="utf-8"), rel)
            except SyntaxError as exc:
                errors.append(f"{rel}:{exc.lineno}: {exc.msg}")
        self.assertEqual(errors, [])

    def test_startup_modules_import(self):
        # Imported lazily inside the app lifespan, so a broken one only fails in production.
        import features.admin.alerts  # noqa: F401
        import features.admin.jobs  # noqa: F401
        import features.ai.routing.health  # noqa: F401
        import shared.bot_commands  # noqa: F401
        import backend.server_app  # noqa: F401


if __name__ == "__main__":
    unittest.main()
