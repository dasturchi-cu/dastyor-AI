"""Preview, Demo PDF, Paid DOCX — mehnat faoliyati bir xil chiqishi kerak."""
from __future__ import annotations

import io
import re
import unittest
import zipfile

from backend.services.document_render.context import build_obyektivka_render_context
from backend.services.render_service import render_obyektivka_html
from features.obyektivka.docx_template import generate_obyektivka_docx_bytes
from features.obyektivka.malumotnoma_data import build_malumotnoma_data
from features.obyektivka.placeholders import build_placeholder_context
from features.obyektivka.service import _export_docx_sync
from tests.test_obyektivka_malumotnoma_data import _sample_payload


def _docx_plaintext(blob: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
    return re.sub(r"<[^>]+>", " ", xml)


def _employment_markers(payload: dict) -> list[str]:
    mdata = build_malumotnoma_data(payload)
    markers = [mdata["current_job"]] if mdata.get("current_job") else []
    for line in mdata.get("work_lines") or []:
        for part in str(line).split(" - "):
            part = part.strip()
            if part and part not in markers:
                markers.append(part)
    return [m for m in markers if m]


class TestObyektivkaEmploymentParity(unittest.TestCase):
    def _assert_markers_in(self, text: str, markers: list[str], *, label: str) -> None:
        for marker in markers:
            self.assertIn(
                marker,
                text,
                msg=f"{label}: «{marker}» topilmadi",
            )

    def test_all_outputs_share_employment(self):
        raw = _sample_payload()
        markers = _employment_markers(raw)
        self.assertGreaterEqual(len(markers), 3)

        html = render_obyektivka_html(raw, watermark=False, mask_pii=False)
        self._assert_markers_in(html, markers, label="preview_html")

        preview_ctx = build_obyektivka_render_context(raw, watermark=False, mask_pii=False)
        self.assertEqual(len(preview_ctx.get("work_experience") or []), 3)
        self.assertEqual(preview_ctx.get("current_job"), "MCHJ rahbari")

        demo_docx = _docx_plaintext(generate_obyektivka_docx_bytes(raw))
        self._assert_markers_in(demo_docx, markers, label="demo_docx")

        paid_docx, _ = _export_docx_sync(999001, raw)
        self._assert_markers_in(_docx_plaintext(paid_docx), markers, label="paid_docx")

        docx_ctx = build_placeholder_context(raw)
        self.assertIn("MCHJ rahbari", docx_ctx.get("hozirgi_ish", ""))
        self.assertIn("Birinchi ish", docx_ctx.get("mehnat_faoliyati", ""))

    def test_work_place_alias_not_dropped(self):
        raw = {
            "lang": "uz_lat",
            "fullname": "Test User",
            "work_experience": [
                {"year": "2010-2014", "work_place": "Eski ish joyi"},
                {"year": "2015-h.v", "work_place": "Hozirgi ish"},
            ],
        }
        markers = _employment_markers(raw)
        self.assertIn("Hozirgi ish", markers)
        self.assertIn("Eski ish joyi", markers)

        html = render_obyektivka_html(raw, watermark=False, mask_pii=False)
        self._assert_markers_in(html, markers, label="preview_html")

        docx = _docx_plaintext(generate_obyektivka_docx_bytes(raw))
        self._assert_markers_in(docx, markers, label="demo_docx")

    def test_employment_history_alias(self):
        raw = {
            "lang": "uz_lat",
            "employmentHistory": [
                {"from": "2008", "to": "2012", "position": "Mutaxassis"},
            ],
        }
        html = render_obyektivka_html(raw, watermark=False, mask_pii=False)
        self.assertIn("Mutaxassis", html)
        docx = _docx_plaintext(generate_obyektivka_docx_bytes(raw))
        self.assertIn("Mutaxassis", docx)


if __name__ == "__main__":
    unittest.main()
