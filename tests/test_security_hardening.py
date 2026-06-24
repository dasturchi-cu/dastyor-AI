"""Security hardening tests."""
from __future__ import annotations

import unittest

from core.file_validation import validate_image_bytes
from database.connection import init_db
from database.repositories import security_dashboard as sec_dash_repo
from database.repositories import security_events as sec_repo


class TestFileValidation(unittest.TestCase):
    def test_reject_empty_image(self):
        from fastapi import HTTPException

        with self.assertRaises(HTTPException):
            validate_image_bytes(b"")

    def test_accept_minimal_png(self):
        from io import BytesIO

        from PIL import Image

        buf = BytesIO()
        Image.new("RGB", (1, 1), color="red").save(buf, format="PNG")
        kind = validate_image_bytes(buf.getvalue())
        self.assertEqual(kind, "png")

    def test_reject_script_in_image(self):
        from fastapi import HTTPException

        with self.assertRaises(HTTPException):
            validate_image_bytes(b"<script>alert(1)</script>" + b"\xff\xd8\xff" + b"x" * 100)


class TestSecurityDashboard(unittest.TestCase):
    def setUp(self):
        init_db()

    def test_security_snapshot_has_score(self):
        sec_repo.record(event_type="auth_failed", severity="warn", ip="1.2.3.4")
        snap = sec_dash_repo.security_snapshot()
        self.assertIn("security_score", snap)
        self.assertGreaterEqual(snap["security_score"], 0)
        self.assertLessEqual(snap["security_score"], 100)


if __name__ == "__main__":
    unittest.main()
