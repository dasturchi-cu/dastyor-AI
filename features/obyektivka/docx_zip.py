"""ZIP/XML-level DOCX operations — clone reference layout, replace text only."""

from __future__ import annotations

import html
import re
import shutil
import zipfile
from copy import deepcopy
from pathlib import Path

from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"
W = f"{{{W_NS}}}"


def escape_xml_text(value: str) -> str:
    return html.escape(value or "", quote=False)


def read_parts(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path, "r") as zin:
        return {name: zin.read(name) for name in zin.namelist()}


def write_parts(path: Path, parts: dict[str, bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in parts.items():
            zout.writestr(name, data)


def replace_text_in_xml(xml: str, replacements: list[tuple[str, str]]) -> str:
    for old, new in sorted(replacements, key=lambda x: -len(x[0])):
        if old and old in xml:
            xml = xml.replace(old, new)
    return xml


def apply_placeholder_context(xml: str, context: dict[str, str]) -> str:
    for key, value in context.items():
        xml = xml.replace(f"{{{{{key}}}}}", escape_xml_text(value))
    return xml


def _first_child(tc: etree._Element, tag: str) -> etree._Element | None:
    for child in tc:
        if child.tag == tag:
            return child
    return None


def _clone_or_none(el: etree._Element | None) -> etree._Element | None:
    return deepcopy(el) if el is not None else None


def set_table_cell_placeholder(tc: etree._Element, placeholder: str) -> None:
    """Replace cell inner XML but keep w:tcPr (width, borders, merge)."""
    tc_pr = _first_child(tc, f"{W}tcPr")
    first_p = _first_child(tc, f"{W}p")
    p_pr = _first_child(first_p, f"{W}pPr") if first_p is not None else None
    first_r = _first_child(first_p, f"{W}r") if first_p is not None else None
    r_pr = _first_child(first_r, f"{W}rPr") if first_r is not None else None

    for child in list(tc):
        if child.tag != f"{W}tcPr":
            tc.remove(child)

    p = etree.SubElement(tc, f"{W}p")
    cloned_p_pr = _clone_or_none(p_pr)
    if cloned_p_pr is not None:
        p.append(cloned_p_pr)
    r = etree.SubElement(p, f"{W}r")
    cloned_r_pr = _clone_or_none(r_pr)
    if cloned_r_pr is not None:
        r.append(cloned_r_pr)
    t = etree.SubElement(r, f"{W}t")
    if placeholder[:1].isspace() or placeholder[-1:].isspace():
        t.set(f"{{{XML_NS}}}space", "preserve")
    t.text = placeholder


def patch_relatives_table(xml_bytes: bytes, row_placeholders: list[list[str]]) -> bytes:
    """row_placeholders[col1..col4] per data row (skip header)."""
    root = etree.fromstring(xml_bytes)
    tables = root.findall(f".//{W}tbl")
    if not tables:
        return xml_bytes
    table = tables[0]
    rows = table.findall(f"{W}tr")
    for row, placeholders in zip(rows[1:], row_placeholders):
        cells = row.findall(f"{W}tc")
        for col_idx, ph in enumerate(placeholders, start=1):
            if col_idx < len(cells) and ph:
                set_table_cell_placeholder(cells[col_idx], ph)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def mark_photo_placeholder(xml: str) -> str:
    return re.sub(
        r"<w:t[^>]*>Оқ фондаги[^<]*</w:t>",
        "<w:t>{{photo}}</w:t>",
        xml,
        count=1,
    )


def clone_with_replacements(
    src: Path,
    dst: Path,
    *,
    replacements: list[tuple[str, str]],
    relatives_rows: list[list[str]] | None = None,
    photo_placeholder: bool = True,
) -> None:
    shutil.copy2(src, dst)
    parts = read_parts(dst)
    xml = parts["word/document.xml"].decode("utf-8")
    xml = replace_text_in_xml(xml, replacements)
    if photo_placeholder:
        xml = mark_photo_placeholder(xml)
    xml_bytes = xml.encode("utf-8")
    if relatives_rows:
        xml_bytes = patch_relatives_table(xml_bytes, relatives_rows)
    parts["word/document.xml"] = xml_bytes
    write_parts(dst, parts)


def render_template(template: Path, context: dict[str, str], output: Path) -> None:
    shutil.copy2(template, output)
    parts = read_parts(output)
    xml = parts["word/document.xml"].decode("utf-8")
    xml = apply_placeholder_context(xml, context)
    parts["word/document.xml"] = xml.encode("utf-8")
    write_parts(output, parts)


def render_template_bytes(template: Path, context: dict[str, str]) -> bytes:
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="oby_zip_")) / "out.docx"
    try:
        render_template(template, context, tmp)
        return tmp.read_bytes()
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)


def count_page_breaks(path: Path) -> int:
    xml = read_parts(path)["word/document.xml"].decode("utf-8")
    return xml.count('w:type="page"')
