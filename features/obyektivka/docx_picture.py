"""Floating picture helper for official Obyektivka header (namuna VML joylashuvi)."""

from __future__ import annotations

from copy import deepcopy

from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Emu, Length
from docx.text.paragraph import Paragraph


def _emu(length: Length | int) -> int:
    return int(length)


def add_floating_picture(
    paragraph: Paragraph,
    image_path: str,
    *,
    width: Length,
    height: Length,
    pos_x: Length | None = None,
    pos_y: Length | None = None,
) -> None:
    """Insert a page-anchored picture (top-right), converted from inline."""
    run = paragraph.add_run()
    run.add_picture(image_path, width=width, height=height)
    inlines = run._r.xpath(".//wp:inline")
    if not inlines:
        return
    inline = inlines[0]
    anchor = OxmlElement("wp:anchor")
    anchor.set(qn("wp:distT"), "0")
    anchor.set(qn("wp:distB"), "0")
    anchor.set(qn("wp:distL"), "0")
    anchor.set(qn("wp:distR"), "0")
    anchor.set(qn("wp:simplePos"), "0")
    anchor.set(qn("wp:relativeHeight"), "251658240")
    anchor.set(qn("wp:behindDoc"), "0")
    anchor.set(qn("wp:locked"), "0")
    anchor.set(qn("wp:layoutInCell"), "1")
    anchor.set(qn("wp:allowOverlap"), "1")

    simple_pos = OxmlElement("wp:simplePos")
    simple_pos.set("x", "0")
    simple_pos.set("y", "0")
    anchor.append(simple_pos)

    pos_h = OxmlElement("wp:positionH")
    pos_h.set(qn("wp:relativeFrom"), "column")
    if pos_x is not None:
        off = OxmlElement("wp:posOffset")
        off.text = str(_emu(pos_x))
        pos_h.append(off)
    else:
        align = OxmlElement("wp:align")
        align.text = "right"
        pos_h.append(align)
    anchor.append(pos_h)

    pos_v = OxmlElement("wp:positionV")
    pos_v.set(qn("wp:relativeFrom"), "paragraph")
    off_v = OxmlElement("wp:posOffset")
    off_v.text = str(_emu(pos_y or Emu(0)))
    pos_v.append(off_v)
    anchor.append(pos_v)

    extent = inline.find(qn("wp:extent"))
    if extent is not None:
        anchor.append(deepcopy(extent))
    effect = inline.find(qn("wp:effectExtent"))
    if effect is not None:
        anchor.append(deepcopy(effect))

    doc_pr = inline.find(qn("wp:docPr"))
    if doc_pr is not None:
        anchor.append(deepcopy(doc_pr))

    c_nv = inline.find(qn("wp:cNvGraphicFramePr"))
    if c_nv is not None:
        anchor.append(deepcopy(c_nv))

    graphic = inline.find(qn("a:graphic"))
    if graphic is not None:
        anchor.append(deepcopy(graphic))

    inline.getparent().replace(inline, anchor)
