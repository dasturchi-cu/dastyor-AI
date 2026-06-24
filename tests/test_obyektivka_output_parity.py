"""Preview, demo, and paid DOCX must share identical body layout from master template."""
from __future__ import annotations

import unittest
import zipfile
from pathlib import Path

from features.obyektivka.docx_fonts import collect_font_sizes, disallowed_sizes
from features.obyektivka.docx_template import generate_obyektivka_docx_bytes
from features.obyektivka.docx_watermark import DEFAULT_WATERMARK_TEXT
from features.obyektivka.docx_zip import count_page_breaks
from features.obyektivka.layout import REL_COL_DXA
from features.obyektivka.objective_data import buildObjectiveData, build_placeholder_context
from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "templates" / "obyektivka_master.docx"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"


def _sample_payload() -> dict:
    return {
        "lang": "uz_cyr",
        "fullname": "Эшматов Ботир Баҳодирович",
        "birthdate": "25.10.1960",
        "birthplace": "Тошкент вилояти, Қибрай тумани",
        "nation": "ўзбек",
        "party": "йўқ",
        "education": "олий",
        "graduated": "1982 й. Тошкент давлат университети",
        "specialty": "иқтисодчи",
        "degree": "иқтисод фанлари доктори",
        "scientific_title": "профессор",
        "languages": "рус, инглиз тиллари",
        "military_rank": "йўқ",
        "awards": "2005 й. медал",
        "departmental_awards": "2008 й. нишон",
        "deputy": "2024 й. депутат",
        "work_experience": [
            {"f": "1977", "t": "1982", "d": "Талаба"},
            {"f": "2007", "t": "h.v", "d": "МЧЖ раҳбари", "fs": "5 oktabr"},
        ],
        "relatives": [
            {
                "degree": "Отаси",
                "fullname": "Test Ota",
                "birth_year_place": "1935 йил",
                "work_place": "Пенсияда",
                "address": "Тошкент",
            }
        ],
    }


def _load_root(docx_bytes: bytes) -> etree._Element:
    with zipfile.ZipFile(io := __import__("io").BytesIO(docx_bytes)) as zf:
        return etree.fromstring(zf.read("word/document.xml"))


def _margins_twips(root: etree._Element) -> dict[str, str]:
    sect = root.find(f".//{W}sectPr")
    pg = sect.find(f"{W}pgMar") if sect is not None else None
    if pg is None:
        return {}
    return {k: pg.get(f"{W}{k}") or "" for k in ("top", "right", "bottom", "left")}


def _table_grid_dxa(root: etree._Element) -> list[str]:
    tbl = root.find(f".//{W}tbl")
    if tbl is None:
        return []
    g = tbl.find(f"{W}tblGrid")
    if g is None:
        return []
    return [c.get(f"{W}w") or "" for c in g.findall(f"{W}gridCol")]


def _body_text(docx_bytes: bytes) -> str:
    root = _load_root(docx_bytes)
    return "".join(t.text or "" for t in root.findall(f".//{W}t"))


class TestObyektivkaOutputParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not MASTER.is_file():
            raise unittest.SkipTest("master docx missing")
        payload = _sample_payload()
        cls.preview_bytes = generate_obyektivka_docx_bytes(payload, watermark=False)
        cls.paid_bytes = generate_obyektivka_docx_bytes(payload, watermark=False)
        cls.demo_bytes = generate_obyektivka_docx_bytes(payload, watermark=True)

    def test_build_objective_data_single_mapper(self):
        raw = _sample_payload()
        obj = buildObjectiveData(raw)
        ctx = build_placeholder_context(raw)
        self.assertEqual(obj["full_name"], ctx["fish"])
        self.assertEqual(obj["current_position"], ctx["hozirgi_ish"])
        self.assertEqual(obj["current_position_year"], ctx["hozirgi_yil"])
        self.assertEqual(obj["work_history"][0], ctx["mehnat_faoliyati"])

    def test_preview_equals_paid_docx(self):
        self.assertEqual(self.preview_bytes, self.paid_bytes)

    def test_page_count_matches_master(self):
        import tempfile

        for label, data in (("preview", self.preview_bytes), ("demo", self.demo_bytes)):
            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
                tmp.write(data)
                path = Path(tmp.name)
            try:
                self.assertEqual(
                    count_page_breaks(path),
                    count_page_breaks(MASTER),
                    f"{label} page breaks differ from master",
                )
            finally:
                path.unlink(missing_ok=True)

    def test_margins_and_tables_identical_except_watermark(self):
        preview_root = _load_root(self.preview_bytes)
        demo_root = _load_root(self.demo_bytes)
        self.assertEqual(_margins_twips(preview_root), _margins_twips(demo_root))
        self.assertEqual(_table_grid_dxa(preview_root), _table_grid_dxa(demo_root))
        self.assertEqual(_table_grid_dxa(preview_root), [str(w) for w in REL_COL_DXA])

    def test_font_sizes_from_reference(self):
        root = _load_root(self.preview_bytes)
        sizes = collect_font_sizes(root)
        bad = disallowed_sizes(sizes)
        self.assertEqual(bad, [], f"non-reference font sizes: {bad}")

    def test_demo_has_watermark_header_only(self):
        with zipfile.ZipFile(__import__("io").BytesIO(self.demo_bytes)) as zf:
            names = zf.namelist()
            self.assertIn("word/header1.xml", names)
            header = zf.read("word/header1.xml").decode("utf-8")
            self.assertIn(DEFAULT_WATERMARK_TEXT, header)
        with zipfile.ZipFile(__import__("io").BytesIO(self.preview_bytes)) as zf:
            self.assertNotIn("word/header1.xml", zf.namelist())
        self.assertEqual(_body_text(self.preview_bytes), _body_text(self.demo_bytes))

    def test_current_job_in_top_block_and_work_history(self):
        text = _body_text(self.preview_bytes)
        self.assertIn("МЧЖ раҳбари", text)
        self.assertGreaterEqual(text.count("МЧЖ раҳбари"), 2)
        self.assertIn("ҳ.в", text)


if __name__ == "__main__":
    unittest.main()
