"""Obyektivka DOCX typography — official label/value hierarchy."""

from __future__ import annotations

import html
import re
from typing import Any

from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"
VAL = f"{{{W_NS}}}val"

# Hint text only — not a data value field.
VALUE_EXCLUDE = frozenset({"photo"})

_PLACEHOLDER_RE = re.compile(r"\{\{([^{}]+)\}\}")


def escape_xml_text(value: str) -> str:
    return html.escape(value or "", quote=False)


def _run_text(r_el: etree._Element) -> str:
    return "".join(t.text or "" for t in r_el.findall(f".//{W}t"))


def _set_text_on_run(r_el: etree._Element, text: str) -> None:
    ts = r_el.findall(f".//{W}t")
    if not ts:
        t = etree.SubElement(r_el, f"{W}t")
        t.text = text
        return
    ts[0].text = text
    for t in ts[1:]:
        t.text = ""


def _r_pr(r_el: etree._Element) -> etree._Element:
    rpr = r_el.find(f"{W}rPr")
    if rpr is None:
        rpr = etree.Element(f"{W}rPr")
        r_el.insert(0, rpr)
    return rpr


def _set_bool(rpr: etree._Element, tag: str, on: bool) -> None:
    for el in rpr.findall(f"{W}{tag}"):
        rpr.remove(el)
    el = etree.SubElement(rpr, f"{W}{tag}")
    if not on:
        el.set(VAL, "0")


def _set_underline(rpr: etree._Element, on: bool) -> None:
    for el in rpr.findall(f"{W}u"):
        rpr.remove(el)
    if on:
        el = etree.SubElement(rpr, f"{W}u")
        el.set(VAL, "single")


def _set_color_black(rpr: etree._Element) -> None:
    for el in rpr.findall(f"{W}color"):
        rpr.remove(el)
    c = etree.SubElement(rpr, f"{W}color")
    c.set(VAL, "000000")


def apply_value_rpr(r_el: etree._Element) -> None:
    """Value: black, normal weight, single underline."""
    rpr = _r_pr(r_el)
    _set_bool(rpr, "b", False)
    _set_bool(rpr, "bCs", False)
    _set_underline(rpr, True)
    _set_color_black(rpr)


def apply_label_rpr(r_el: etree._Element) -> None:
    """Label: black, bold, no underline."""
    rpr = _r_pr(r_el)
    _set_bool(rpr, "b", True)
    _set_bool(rpr, "bCs", True)
    _set_underline(rpr, False)
    _set_color_black(rpr)


def _is_bold_run(r_el: etree._Element) -> bool:
    rpr = r_el.find(f"{W}rPr")
    if rpr is None:
        return False
    b = rpr.find(f"{W}b")
    return b is not None and b.get(VAL) != "0"


def apply_document_typography(root: etree._Element, context: dict[str, str]) -> None:
    """Replace placeholders and apply label/value styles across the document."""
    value_run_ids: set[int] = set()
    sorted_items = sorted(context.items(), key=lambda item: -len(item[0]))

    for r_el in root.findall(f".//{W}r"):
        text = _run_text(r_el)
        if not text or "{{" not in text:
            continue

        new_text = text
        touches_value = False
        for key, raw in sorted_items:
            ph = f"{{{{{key}}}}}"
            if ph not in new_text:
                continue
            new_text = new_text.replace(ph, escape_xml_text(raw))
            if key not in VALUE_EXCLUDE:
                touches_value = True

        if new_text == text:
            continue

        _set_text_on_run(r_el, new_text)
        if touches_value:
            value_run_ids.add(id(r_el))
            apply_value_rpr(r_el)

    for r_el in root.findall(f".//{W}r"):
        if id(r_el) in value_run_ids:
            continue
        if not _is_bold_run(r_el):
            continue
        if not _run_text(r_el).strip():
            continue
        apply_label_rpr(r_el)


def apply_master_template_styles(root: etree._Element) -> None:
    """Style placeholder runs as values; reinforce label runs in the master template."""
    for r_el in root.findall(f".//{W}r"):
        text = _run_text(r_el)
        if "{{" in text and "}}" in text:
            apply_value_rpr(r_el)

    for r_el in root.findall(f".//{W}r"):
        if not _is_bold_run(r_el):
            continue
        if not _run_text(r_el).strip():
            continue
        apply_label_rpr(r_el)


def render_document_xml(xml_bytes: bytes, context: dict[str, str]) -> bytes:
    from features.obyektivka.docx_fonts import enforce_reference_fonts

    root = etree.fromstring(xml_bytes)
    apply_document_typography(root, context)
    enforce_reference_fonts(root, context)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def run_has_underline(r_el: etree._Element) -> bool:
    rpr = r_el.find(f"{W}rPr")
    if rpr is None:
        return False
    u = rpr.find(f"{W}u")
    return u is not None and u.get(VAL) != "none"


def find_runs_containing(root: etree._Element, needle: str) -> list[etree._Element]:
    out: list[etree._Element] = []
    for r_el in root.findall(f".//{W}r"):
        if needle in _run_text(r_el):
            out.append(r_el)
    return out


def typography_summary(root: etree._Element) -> dict[str, Any]:
    labels = 0
    values = 0
    for r_el in root.findall(f".//{W}r"):
        text = _run_text(r_el).strip()
        if not text:
            continue
        if run_has_underline(r_el):
            values += 1
        elif _is_bold_run(r_el):
            labels += 1
    return {"label_runs": labels, "value_runs": values}
