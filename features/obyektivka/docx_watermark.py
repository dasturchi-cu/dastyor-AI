"""Diagonal semi-transparent watermark for demo DOCX exports."""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

from lxml import etree

from features.obyektivka.docx_zip import read_parts, write_parts

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
V_NS = "urn:schemas-microsoft-com:vml"
O_NS = "urn:schemas-microsoft-com:office:office"
WPC_NS = "http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas"
W = f"{{{W_NS}}}"
R = f"{{{R_NS}}}"
CT = f"{{{CT_NS}}}"
REL = f"{{{REL_NS}}}"

DEFAULT_WATERMARK_TEXT = "@DastyorAiBot"


def watermark_text() -> str:
    return (os.getenv("OBY_DEMO_WATERMARK_TEXT") or DEFAULT_WATERMARK_TEXT).strip() or DEFAULT_WATERMARK_TEXT


def _watermark_opacity() -> str:
    try:
        v = float(os.getenv("OBY_DEMO_WATERMARK_OPACITY", "0.35") or "0.35")
    except ValueError:
        v = 0.35
    v = max(0.15, min(0.55, v))
    return f"{v:.2f}"


def _header_xml(text: str) -> bytes:
    opacity = _watermark_opacity()
    safe = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:hdr xmlns:w="{W_NS}" xmlns:v="{V_NS}" xmlns:o="{O_NS}" xmlns:r="{R_NS}">
  <w:p>
    <w:pPr>
      <w:pStyle w:val="Header"/>
    </w:pPr>
    <w:r>
      <w:pict>
        <v:shapetype id="_x0000_t136" coordsize="21600,21600" o:spt="136" adj="10800"
          path="m@7,l@8,m@5,21600l@6,21600e">
          <v:formulas>
            <v:f eqn="sum #0 0 10800"/>
            <v:f eqn="prod #0 2 1"/>
            <v:f eqn="sum #0 0 10800"/>
            <v:f eqn="sum #0 0 0"/>
            <v:f eqn="sum #0 0 0"/>
            <v:f eqn="sum #0 0 0"/>
            <v:f eqn="sum #0 0 0"/>
            <v:f eqn="sum #0 0 0"/>
            <v:f eqn="sum #0 0 0"/>
            <v:f eqn="sum #0 0 0"/>
          </v:formulas>
          <v:path textpathok="t" o:connecttype="custom"
            o:connectlocs="@9,0;@10,10800;@11,21600;@12,10800"
            o:connectangles="270,180,90,0"/>
          <v:textpath on="t" fitshape="t"/>
          <v:handles>
            <v:h position="#0,bottomRight" xrange="6629,14971"/>
            <v:h position="bottomRight,#0" yrange="4459,10800"/>
          </v:handles>
        </v:shapetype>
        <v:shape id="ObyDemoWatermark" type="#_x0000_t136"
          style="position:absolute;left:0;text-align:left;margin-left:0;margin-top:0;width:468pt;height:117pt;rotation:315;z-index:-251658240;mso-position-horizontal:center;mso-position-horizontal-relative:margin;mso-position-vertical:center;mso-position-vertical-relative:margin"
          o:allowincell="f" fillcolor="#c0c0c0" stroked="f">
          <v:fill opacity="{opacity}"/>
          <v:textpath style="font-family:&quot;Times New Roman&quot;;font-size:54pt;font-weight:bold" string="{safe}"/>
        </v:shape>
      </w:pict>
    </w:r>
  </w:p>
</w:hdr>"""
    return xml.encode("utf-8")


def _next_rid(rels_xml: bytes) -> str:
    ids = [int(m.group(1)) for m in re.finditer(rb'Id="rId(\d+)"', rels_xml)]
    return f"rId{(max(ids) + 1) if ids else 1}"


def _ensure_content_type(parts: dict[str, bytes], part_name: str, content_type: str) -> None:
    root = etree.fromstring(parts["[Content_Types].xml"])
    for override in root.findall(f"{CT}Override"):
        if override.get("PartName") == part_name:
            return
    override = etree.SubElement(root, f"{CT}Override")
    override.set("PartName", part_name)
    override.set("ContentType", content_type)
    parts["[Content_Types].xml"] = etree.tostring(
        root, xml_declaration=True, encoding="UTF-8", standalone=True
    )


def apply_demo_watermark(docx_path: Path, *, text: str | None = None) -> None:
    """Inject diagonal watermark into every section via default header."""
    label = text or watermark_text()
    parts = read_parts(docx_path)
    header_name = "word/header1.xml"
    rels_name = "word/_rels/document.xml.rels"

    parts[header_name] = _header_xml(label)
    _ensure_content_type(
        parts,
        "/word/header1.xml",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml",
    )

    rels_root = etree.fromstring(parts[rels_name])
    for rel in rels_root.findall(f"{REL}Relationship"):
        if rel.get("Type", "").endswith("/header"):
            rels_root.remove(rel)
    header_rid = _next_rid(parts[rels_name])
    rel = etree.SubElement(rels_root, f"{REL}Relationship")
    rel.set("Id", header_rid)
    rel.set(
        "Type",
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/header",
    )
    rel.set("Target", "header1.xml")
    parts[rels_name] = etree.tostring(
        rels_root, xml_declaration=True, encoding="UTF-8", standalone=True
    )

    doc_root = etree.fromstring(parts["word/document.xml"])
    for sect in doc_root.findall(f".//{W}sectPr"):
        for child in list(sect):
            if child.tag == f"{W}headerReference":
                sect.remove(child)
        href = etree.Element(f"{W}headerReference")
        href.set(f"{W}type", "default")
        href.set(f"{R}id", header_rid)
        sect.insert(0, href)
    parts["word/document.xml"] = etree.tostring(
        doc_root, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    write_parts(docx_path, parts)


def apply_demo_watermark_bytes(docx_bytes: bytes, *, text: str | None = None) -> bytes:
    import shutil
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="oby_wm_")) / f"wm_{uuid.uuid4().hex}.docx"
    try:
        tmp.write_bytes(docx_bytes)
        apply_demo_watermark(tmp, text=text)
        return tmp.read_bytes()
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)
