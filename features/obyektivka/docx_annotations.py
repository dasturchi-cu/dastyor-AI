"""Strip developer annotations from reference clone — never render into output.

Visual notes in «Намуна Объективка (18).doc» (Шрифт labels, mm markers,
speech bubbles, arrows, training comments) are formatting guidance only.
"""

from __future__ import annotations

import re
from typing import Any

from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"

# Exact annotation fragments that must never appear in generated documents.
GARBAGE_EXACT = frozenset(
    {
        "Шрифт 11",
        "Шрифт 14",
        "Шрифт 12",
        "Шрифт 1",
        "Shrift 11",
        "Shrift 14",
        "Shrift 12",
        "Shrift 1",
        "1",
        "2",
        "4",
        "8",
        "мм",
        "mm",
        "пт",
        "pt",
        "0 пт",
        "0 pt",
        "8 пт0 пт",
        "4 пт0 пт",
        "8 мм0 мм",
        "4 мм0 мм",
        "8 mm0 mm",
        "4 mm0 mm",
    }
)

_GARBAGE_RE = re.compile(
    r"^Шрифт\s+\d+$|^Shrift\s+\d+$|^\d+\s*(?:пт|pt)0\s*(?:пт|pt)$|^\d+\s*(?:мм|mm)0\s*(?:мм|mm)$",
    re.IGNORECASE,
)

_TRAINING_RE = re.compile(
    r"Ҳарбий\s*\(махсус\)\s*унвони\s*фақат.*?кўрсатилади\.?",
    re.IGNORECASE | re.DOTALL,
)

_TRAINING_RUN_FRAGMENTS = frozenset(
    {
        "Ҳарбий (махсус) унвони",
        "Ҳарбий (махсус) унвони ",
        "фақат",
        "Harbiy (maxsus) unvoni",
        "Harbiy (maxsus) unvoni ",
        "faqat",
    }
)


def _run_text(r_el: etree._Element) -> str:
    return "".join(t.text or "" for t in r_el.findall(f".//{W}t"))


def _paragraph_text(p_el: etree._Element) -> str:
    return "".join(t.text or "" for t in p_el.findall(f".//{W}t")).strip()


def is_garbage_run(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    if t in GARBAGE_EXACT:
        return True
    return bool(_GARBAGE_RE.match(t))


def is_training_run(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    if t in _TRAINING_RUN_FRAGMENTS:
        return True
    if "кўрсатилади" in t and "ҳарбий" in t:
        return True
    if "ko'rsatiladi" in t.lower() and "harbiy" in t.lower():
        return True
    return bool(_TRAINING_RE.fullmatch(t))


def is_annotation_text(text: str) -> bool:
    return is_garbage_run(text) or is_training_run(text)


def _is_photo_pict(pict_el: etree._Element) -> bool:
    xml = etree.tostring(pict_el)
    return b"v:rect" in xml and b"mso-width-relative:page" in xml


def remove_garbage_runs(root: etree._Element) -> int:
    removed = 0
    for p_el in root.findall(f".//{W}p"):
        for r_el in list(p_el.findall(f"{W}r")):
            if is_garbage_run(_run_text(r_el)) or is_training_run(_run_text(r_el)):
                p_el.remove(r_el)
                removed += 1
    return removed


def remove_annotation_picts(root: etree._Element) -> int:
    """Remove arrows, speech bubbles, and label shapes; keep photo VML frame."""
    removed = 0
    for r_el in root.findall(f".//{W}r"):
        pict = r_el.find(f"{W}pict")
        if pict is None:
            continue
        if _is_photo_pict(pict):
            continue
        xml = etree.tostring(pict)
        texts = [_run_text(rr) for rr in pict.findall(f".//{W}r")]
        if any(is_annotation_text(t) for t in texts):
            r_el.remove(pict)
            removed += 1
            continue
        if b"v:line" in xml or b"v:polyline" in xml:
            r_el.remove(pict)
            removed += 1
            continue
        if b"v:shape" in xml and not any(t.strip() for t in texts):
            r_el.remove(pict)
            removed += 1
    return removed


def remove_pure_garbage_paragraphs(root: etree._Element) -> int:
    removed = 0
    body = root.find(f"{W}body")
    if body is None:
        return 0
    for p_el in list(body.findall(f"{W}p")):
        text = _paragraph_text(p_el)
        if not text:
            continue
        if text in GARBAGE_EXACT or _GARBAGE_RE.match(text):
            body.remove(p_el)
            removed += 1
            continue
        if _TRAINING_RE.fullmatch(text):
            body.remove(p_el)
            removed += 1
    return removed


def remove_empty_body_paragraphs(root: etree._Element) -> int:
    removed = 0
    body = root.find(f"{W}body")
    if body is None:
        return 0
    for p_el in list(body.findall(f"{W}p")):
        text = _paragraph_text(p_el)
        has_pict = p_el.find(f".//{W}pict") is not None
        has_drawing = p_el.find(f".//{W}drawing") is not None
        if not text and not has_pict and not has_drawing:
            body.remove(p_el)
            removed += 1
    return removed


def patch_tamomlagan_placeholder(root: etree._Element) -> bool:
    """Replace split graduation runs with {{tamomlagan}} after {{malumoti}}."""
    for p_el in root.findall(f".//{W}p"):
        text = _paragraph_text(p_el)
        if "{{malumoti}}" not in text and "олий" not in text and "{{tamomlagan}}" in text:
            continue
        if "{{tamomlagan}}" in text:
            return False
        runs = p_el.findall(f"{W}r")
        combined = ""
        start_idx: int | None = None
        for idx, r_el in enumerate(runs):
            part = _run_text(r_el)
            combined += part
            if "1982" in part or (start_idx is not None and part.strip()):
                if start_idx is None and "1982" in part:
                    start_idx = idx
        if start_idx is None:
            continue
        if "университети" not in combined and "universitet" not in combined.lower():
            continue
        for r_el in list(runs[start_idx:]):
            if "университети" in _run_text(r_el) or "1982" in _run_text(r_el) or _run_text(r_el) in {".", ""}:
                p_el.remove(r_el)
            elif _run_text(r_el).strip().startswith(" Тошкент") or _run_text(r_el).strip().startswith(" Toshkent"):
                p_el.remove(r_el)
        r_el = etree.SubElement(p_el, f"{W}r")
        t = etree.SubElement(r_el, f"{W}t")
        t.text = "{{tamomlagan}}"
        return True
    return False


def strip_reference_annotations(root: etree._Element) -> dict[str, Any]:
    """Full annotation strip for reference-lock / template-clone mode."""
    stats: dict[str, Any] = {}
    stats["garbage_runs"] = remove_garbage_runs(root)
    stats["annotation_picts"] = remove_annotation_picts(root)
    stats["garbage_paragraphs"] = remove_pure_garbage_paragraphs(root)
    stats["empty_paragraphs"] = remove_empty_body_paragraphs(root)
    stats["tamomlagan_patched"] = patch_tamomlagan_placeholder(root)
    return stats


def collect_annotation_violations(root: etree._Element) -> list[str]:
    """Return human-readable violations for tests / QA."""
    violations: list[str] = []
    for r_el in root.findall(f".//{W}r"):
        text = _run_text(r_el).strip()
        if not text:
            continue
        if is_garbage_run(text):
            violations.append(f"garbage run: {text!r}")
        elif is_training_run(text):
            violations.append(f"training run: {text!r}")
    for r_el in root.findall(f".//{W}r"):
        pict = r_el.find(f"{W}pict")
        if pict is None or _is_photo_pict(pict):
            continue
        xml = etree.tostring(pict)
        if b"v:line" in xml or b"v:polyline" in xml:
            violations.append("arrow pict present")
        texts = [_run_text(rr) for rr in pict.findall(f".//{W}r")]
        if any(is_annotation_text(t) for t in texts):
            violations.append(f"annotation pict text: {texts!r}")
    return violations
