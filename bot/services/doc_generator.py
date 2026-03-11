from __future__ import annotations

import os
from io import BytesIO
from typing import Any, Dict, List, Optional

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

_BASE_FONT_NAME = "Times New Roman"
_BASE_FONT_SIZE_PT = 12


def _init_document() -> Document:
    doc = Document()
    for section in doc.sections:
        section.top_margin = Cm(2.0)
        section.bottom_margin = Cm(2.0)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(1.5)

    style = doc.styles["Normal"]
    style.font.name = _BASE_FONT_NAME
    style.font.size = Pt(_BASE_FONT_SIZE_PT)
    style.paragraph_format.space_before = Pt(0)
    style.paragraph_format.space_after = Pt(0)
    return doc


def _add_centered_title(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.bold = True
    run.font.name = _BASE_FONT_NAME
    run.font.size = Pt(_BASE_FONT_SIZE_PT + 2)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(12)


def _add_section_title(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.bold = True
    run.font.name = _BASE_FONT_NAME
    run.font.size = Pt(_BASE_FONT_SIZE_PT)
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(8)


def _add_labeled_paragraph(
    doc: Document,
    label: str,
    value: Optional[str],
    space_after_pt: float = 4.0,
) -> None:
    p = doc.add_paragraph()
    run_label = p.add_run(label + " ")
    run_label.bold = True
    run_label.font.name = _BASE_FONT_NAME
    run_label.font.size = Pt(_BASE_FONT_SIZE_PT)

    run_val = p.add_run((value or "").strip())
    run_val.bold = False
    run_val.font.name = _BASE_FONT_NAME
    run_val.font.size = Pt(_BASE_FONT_SIZE_PT)
    p.paragraph_format.space_after = Pt(space_after_pt)


def _normalize_work_experience(raw: Any) -> List[Dict[str, str]]:
    if not raw:
        return []
    if isinstance(raw, list):
        items = raw
    else:
        try:
            import json

            items = json.loads(raw)
        except Exception:
            return []

    result: List[Dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        year = (item.get("year") or item.get("years") or "").strip()
        pos = (
            item.get("position")
            or item.get("pos")
            or item.get("description")
            or ""
        ).strip()
        if not (year or pos):
            continue
        result.append({"year": year, "position": pos})
    return result


def _normalize_relatives(raw: Any) -> List[Dict[str, str]]:
    if not raw:
        return []
    if isinstance(raw, list):
        items = raw
    else:
        try:
            import json

            items = json.loads(raw)
        except Exception:
            return []

    result: List[Dict[str, str]] = []
    for r in items:
        if not isinstance(r, dict):
            continue
        result.append(
            {
                "type": (
                    r.get("type")
                    or r.get("degree")
                    or r.get("kin")
                    or ""
                ).strip(),
                "name": (
                    r.get("name")
                    or r.get("fullname")
                    or r.get("fish")
                    or ""
                ).strip(),
                "birth": (
                    r.get("birth")
                    or r.get("birth_year_place")
                    or ""
                ).strip(),
                "job": (
                    r.get("job")
                    or r.get("work_place")
                    or r.get("work")
                    or ""
                ).strip(),
                "addr": (r.get("addr") or r.get("address") or "").strip(),
            }
        )
    return result


class ObyektivkaLayout:
    def __init__(self, data: Dict[str, Any]):
        self.data = data or {}

    def _g(self, key: str, default: str = "") -> str:
        return (self.data.get(key) or default).strip()

    def build_document(self) -> Document:
        doc = _init_document()

        _add_centered_title(doc, "МАЪЛУМОТНОМА")

        personal_fields = [
            ("Туг‘илган йили:", self._g("birthdate")),
            ("Туг‘илган жойи:", self._g("birthplace")),
            ("Миллати:", self._g("nation")),
            ("Партиявийлиги:", self._g("party")),
            ("Ма’лумоти:", self._g("education")),
            ("Тамомлаган:", self._g("graduated")),
            ("Ма’лумоти бўйича мутахассислиги:", self._g("specialty")),
            ("Илмий даражаси:", self._g("degree")),
            ("Илмий унвони:", self._g("scientific_title")),
            ("Қайси чет тилларини билади:", self._g("languages")),
            ("Ҳарбий унвони:", self._g("military_rank")),
            (
                "Давлат мукофотлари билан тақдирланганми:",
                self._g("awards"),
            ),
            (
                "Халқ депутатлари кенгашига сайланганми:",
                self._g("deputy"),
            ),
        ]

        for label, value in personal_fields:
            _add_labeled_paragraph(doc, label, value, space_after_pt=4)

        spacer = doc.add_paragraph()
        spacer.paragraph_format.space_after = Pt(4)

        _add_section_title(doc, "МЕҲНАТ ФАОЛИЯТИ")

        works = _normalize_work_experience(self.data.get("work_experience"))
        if works:
            for item in works:
                year = item.get("year", "").strip()
                pos = item.get("position", "").strip()
                if not (year or pos):
                    continue
                p = doc.add_paragraph()
                p.paragraph_format.space_after = Pt(3)
                if year:
                    r_year = p.add_run(year)
                    r_year.bold = True
                    r_year.font.name = _BASE_FONT_NAME
                    r_year.font.size = Pt(_BASE_FONT_SIZE_PT)
                    p.add_run("  —  ")
                r_pos = p.add_run(pos)
                r_pos.bold = False
                r_pos.font.name = _BASE_FONT_NAME
                r_pos.font.size = Pt(_BASE_FONT_SIZE_PT)
        else:
            p = doc.add_paragraph()
            r = p.add_run("Иш жойлари кўрсатилмаган.")
            r.font.name = _BASE_FONT_NAME
            r.font.size = Pt(_BASE_FONT_SIZE_PT)
            p.paragraph_format.space_after = Pt(4)

        doc.add_page_break()

        p_rel_title = doc.add_paragraph()
        p_rel_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_rel = p_rel_title.add_run(
            "УНИНГ ЯҚИН ҚАРИНДОШЛАРИ ҲАҚИДА МАЪЛУМОТ"
        )
        run_rel.bold = True
        run_rel.font.name = _BASE_FONT_NAME
        run_rel.font.size = Pt(_BASE_FONT_SIZE_PT)
        p_rel_title.paragraph_format.space_before = Pt(0)
        p_rel_title.paragraph_format.space_after = Pt(12)

        relatives = _normalize_relatives(self.data.get("relatives"))
        if relatives:
            for rel in relatives:
                p = doc.add_paragraph()
                p.paragraph_format.space_after = Pt(8)

                def add_line(label: str, value: str) -> None:
                    line_label = p.add_run(label + " ")
                    line_label.bold = True
                    line_label.font.name = _BASE_FONT_NAME
                    line_label.font.size = Pt(_BASE_FONT_SIZE_PT)

                    line_val = p.add_run(value.strip() if value else "")
                    line_val.bold = False
                    line_val.font.name = _BASE_FONT_NAME
                    line_val.font.size = Pt(_BASE_FONT_SIZE_PT)
                    p.add_run("\n")

                add_line("Қариндошлиги:", rel.get("type", ""))
                add_line("Ф.И.Ш.:", rel.get("name", ""))
                add_line("Туг‘илган йили ва жойи:", rel.get("birth", ""))
                add_line("Иш жойи ва лавозими:", rel.get("job", ""))

                last_label = p.add_run("Турар жойи: ")
                last_label.bold = True
                last_label.font.name = _BASE_FONT_NAME
                last_label.font.size = Pt(_BASE_FONT_SIZE_PT)
                last_val = p.add_run(rel.get("addr", "").strip())
                last_val.bold = False
                last_val.font.name = _BASE_FONT_NAME
                last_val.font.size = Pt(_BASE_FONT_SIZE_PT)
        else:
            p = doc.add_paragraph()
            r = p.add_run("Яқин қариндошлар ҳақида маълумот киритилмаган.")
            r.font.name = _BASE_FONT_NAME
            r.font.size = Pt(_BASE_FONT_SIZE_PT)

        return doc


def generate_obyektivka_word(
    data: Dict[str, Any],
    lang: str = "uz_lat",
    is_sample: bool = False,
) -> BytesIO:
    layout = ObyektivkaLayout(data)
    doc = layout.build_document()
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


def generate_obyektivka_docx(
    data: Dict[str, Any],
    photo_path: Optional[str] = None,
    output_dir: str = "temp",
) -> str:
    os.makedirs(output_dir, exist_ok=True)
    stream = generate_obyektivka_word(data)
    safe_name = (data.get("fullname") or "Obyektivka").replace(" ", "_")
    safe_name = safe_name.replace("/", "_")[:30] or "Obyektivka"
    filename = f"obyektivka_{safe_name}_@DastyorAiBot.docx"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "wb") as f:
        f.write(stream.getvalue())
    return filepath


def generate_cv_docx(data: Dict[str, Any], output_dir: str = "temp") -> str:
    from bot.keyboards.doc_generator import generate_cv_docx as _gen

    os.makedirs(output_dir, exist_ok=True)
    return _gen(data, output_dir=output_dir)


def convert_to_pdf_safe(docx_path: str, output_dir: str = "temp") -> Optional[str]:
    return None


if __name__ == "__main__":
    sample = {
        "fullname": "Алиев Али Алиевич",
        "birthdate": "22.02.1990",
        "birthplace": "Тошкент шахри",
        "nation": "Ўзбек",
        "party": "йўқ",
        "education": "Олий",
        "graduated": "Тошкент давлат юриспруденция университети",
        "specialty": "Юрист",
        "degree": "йўқ",
        "scientific_title": "йўқ",
        "languages": "Рус, Инглиз",
        "military_rank": "захирада",
        "awards": "йўқ",
        "deputy": "йўқ",
        "work_experience": [
            {"year": "2010–2015", "position": "Huquqshunos, Adliya vazirligi"},
            {"year": "2015–ҳ.в.", "position": "Bo‘lim boshlig‘i, Adliya vazирлиги"},
        ],
        "relatives": [
            {
                "type": "Отаси",
                "name": "Алиев Вали Алиевич",
                "birth": "1960 й., Тошкент шахри",
                "job": "Нафақада",
                "addr": "Тошкент шахри, ...",
            },
            {
                "type": "Онаси",
                "name": "Алиева Саида Ахмедовна",
                "birth": "1963 й., Тошкент шахри",
                "job": "Уй бекаси",
                "addr": "Тошкент шахри, ...",
            },
        ],
    }
    out_dir = "temp"
    os.makedirs(out_dir, exist_ok=True)
    out_path = generate_obyektivka_docx(sample, output_dir=out_dir)
    print(f"Tayyor DOCX: {out_path}")