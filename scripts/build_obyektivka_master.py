"""
Build templates/obyektivka_master.docx from reference — ZIP/XML only (layout clone).
Run: python scripts/build_obyektivka_master.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from features.obyektivka.docx_zip import clone_with_replacements, count_page_breaks, read_parts, write_parts

ROOT = Path(__file__).resolve().parent.parent
REF_DOCX = ROOT / "temp" / "ref_converted.docx"
REF_DOC = ROOT / "Намуна Объективка (18).doc"
OUT = ROOT / "templates" / "obyektivka_master.docx"

TEXT_REPLACEMENTS: list[tuple[str, str]] = [
    ("Эшматов Ботир Баҳодирович", "{{fish}}"),
    ("2007 йил 5 октябрдан:", "{{hozirgi_yil}}"),
    ("25.10.1960", "{{tugilgan_sana}}"),
    ("Тошкент вилояти, Қибрай тумани ", "{{tugilgan_joy}}"),
    ("ўзбек", "{{millati}}"),
    ("олий", "{{malumoti}}"),
    ("1982 й. Тошкент давлат университети (кундузги)", "{{tamomlagan}}"),
    ("иқтисодчи", "{{mutaxassisligi}}"),
    ("иқтисод фанлари доктори", "{{ilmiy_darajasi}}"),
    ("профессор", "{{ilmiy_unvoni}}"),
    ("рус, инглиз тиллари ", "{{chet_tillari}}"),
    (
        "2005 й. “Шуҳрати” медал, 2010 й. “Меҳнат шуҳрати” ордени",
        "{{mukofotlari}}",
    ),
    (
        "2008 й. «Халқ таълим аълочиси» кўкрак нишони, 2017 й. «Ўзбекистон Конституциясига 25 йил» эсдалик нишони, 2025 й. «Ғалабанинг 80 йиллиги» юбилей нишони, 2026 й. «Фидокорона меҳнати учун» кўкрак нишони",
        "{{idoriy_mukofotlari}}",
    ),
    (
        "2024 й.  - ҳ.в. - Халқ депутатлари Тошкент вилояти Кенгаши депутати, Ўзбекистон Республикаси Олий Мажлиси Сенати аъзоси ",
        "{{deputatligi}}",
    ),
    ("1977-1982 йй. - Тошкент давлат университети талабаси", "{{mehnat_faoliyati}}"),
    ("1982-1988 йй. - Тошкент давлат университети иқтисодиёт факультети кичик илмий ходими", "{{mehnat_faoliyati_2}}"),
    ("1988-1991 йй. - Тошкент давлат университети иқтисодиёт факультети аспиранти", "{{mehnat_faoliyati_3}}"),
    (
        "1991-1995 йй. - Тошкент давлат иқтисодиёт университети иқтисодиёт факультети катта илмий ходими",
        "{{mehnat_faoliyati_4}}",
    ),
    (
        "1995-1998 йй. - Тошкент давлат иқтисодиёт университети иқтисодиёт факультети докторанти",
        "{{mehnat_faoliyati_5}}",
    ),
    (
        "1998-2004 йй. - Ўзбекистон Республикаси Иқтисодиёт вазирлиги таълимни ривожлантириш бўлими мутахассиси, етакчи мутахассиси, бош мутахассиси",
        "{{mehnat_faoliyati_6}}",
    ),
    (
        "2004-2007 йй. - Тошкент давлат иқтисодиёт университети микроиқтисодиёт факультети декани",
        "{{mehnat_faoliyati_7}}",
    ),
    (
        "2007 й. -  ҳ.в.  - Андижон вилояти Андижон тумани “Makon Mirzo” масъулияти чекланган жамияти раҳбари",
        "{{mehnat_faoliyati_8}}",
    ),
    (
        "Андижон вилояти Андижон тумани “Makon Mirzo” масъулияти чекланган жамияти раҳбари",
        "{{hozirgi_ish}}",
    ),
]

REL_ROW_PREFIXES: list[tuple[str, str]] = [
    ("Отаси", "ota"),
    ("Онаси", "ona"),
    ("Опаси", "opa"),
    ("Синглиси", "singil"),
    ("Укаси", "uka"),
    ("Укаси", "aka"),
    ("Турмуш ўртоғи", "turmush_ortogi"),
    ("Ўғли", "farzandlar"),
    ("Қизи", "farzandlar_2"),
    ("Ўғли", "farzandlar_3"),
    ("Ўғли", "farzandlar_4"),
    ("Қизи", "farzandlar_5"),
    ("Ўғли", "farzandlar_6"),
    ("Қайнотаси", "qaynota"),
    ("Қайнонаси", "qaynona"),
]


def _build_relatives_rows() -> list[list[str]]:
    rows: list[list[str]] = []
    uka_seen = 0
    for _lbl, prefix in REL_ROW_PREFIXES:
        if _lbl == "Укаси":
            pfx = "uka" if uka_seen == 0 else "aka"
            uka_seen += 1
        else:
            pfx = prefix
        rows.append(
            [
                "{{" + pfx + "}}",
                "{{" + pfx + "_yil}}",
                "{{" + pfx + "_ish}}",
                "{{" + pfx + "_tur}}",
            ]
        )
    return rows


def _patch_party_military(xml: str) -> str:
    """Replace the two йўқ values beside millati / chet_tillari rows."""
    xml = xml.replace("{{millati}}", "{{millati}}", 1)
    # first standalone йўқ after {{millati}} in document order
    xml = re.sub(
        r"({{millati}}</w:t>.*?<w:t[^>]*>)йўқ(</w:t>)",
        r"\1{{partiyaviyligi}}\2",
        xml,
        count=1,
        flags=re.DOTALL,
    )
    xml = re.sub(
        r"({{chet_tillari}}</w:t>.*?<w:t[^>]*>)йўқ(</w:t>)",
        r"\1{{harbiy_unvoni}}\2",
        xml,
        count=1,
        flags=re.DOTALL,
    )
    return xml


def ensure_ref_docx() -> Path:
    if REF_DOCX.is_file():
        return REF_DOCX
    REF_DOCX.parent.mkdir(parents=True, exist_ok=True)
    if REF_DOC.is_file():
        try:
            import win32com.client  # type: ignore

            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            doc = word.Documents.Open(str(REF_DOC.resolve()))
            doc.SaveAs(str(REF_DOCX.resolve()), FileFormat=16)
            doc.Close()
            word.Quit()
            return REF_DOCX
        except Exception as exc:
            print("Word COM conversion failed:", exc, file=sys.stderr)
    raise FileNotFoundError(f"Reference DOCX missing: {REF_DOCX}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    src = ensure_ref_docx()
    OUT.parent.mkdir(parents=True, exist_ok=True)

    clone_with_replacements(
        src,
        OUT,
        replacements=TEXT_REPLACEMENTS,
        relatives_rows=_build_relatives_rows(),
        photo_placeholder=True,
    )

    parts = read_parts(OUT)
    xml = parts["word/document.xml"].decode("utf-8")
    xml = _patch_party_military(xml)
    parts["word/document.xml"] = xml.encode("utf-8")
    write_parts(OUT, parts)

    from features.obyektivka.docx_annotations import strip_reference_annotations
    from features.obyektivka.docx_fonts import enforce_reference_fonts
    from features.obyektivka.docx_typography import apply_master_template_styles
    from lxml import etree

    parts = read_parts(OUT)
    root = etree.fromstring(parts["word/document.xml"])
    strip_reference_annotations(root)
    apply_master_template_styles(root)
    enforce_reference_fonts(root)
    parts["word/document.xml"] = etree.tostring(
        root, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    write_parts(OUT, parts)

    ref_pb = count_page_breaks(src)
    out_pb = count_page_breaks(OUT)
    print("written", OUT)
    print(f"page_breaks: reference={ref_pb} master={out_pb}")
    if ref_pb != out_pb:
        raise SystemExit("FAIL: page break lost during master build")


if __name__ == "__main__":
    main()
