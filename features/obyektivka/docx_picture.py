"""VML pict (v:rect) — namuna «Намуна Объективка (18).doc» bilan 1:1."""

from __future__ import annotations

import html

from docx.image.image import Image
from docx.oxml import parse_xml
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

from features.obyektivka.layout import (
    PHOTO_VML_HEIGHT_PT,
    PHOTO_VML_MARGIN_LEFT_PT,
    PHOTO_VML_MARGIN_TOP_PT,
    PHOTO_VML_WIDTH_PT,
    PHOTO_VML_Z_INDEX,
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
V_NS = "urn:schemas-microsoft-com:vml"
O_NS = "urn:schemas-microsoft-com:office:office"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

_spid = 1029


def _next_spid() -> str:
    global _spid
    _spid += 1
    return f"_x0000_s{_spid}"


def _vml_rect_style() -> str:
    return (
        f"position:absolute;left:0pt;margin-left:{PHOTO_VML_MARGIN_LEFT_PT}pt;"
        f"margin-top:{PHOTO_VML_MARGIN_TOP_PT}pt;height:{PHOTO_VML_HEIGHT_PT}pt;"
        f"width:{PHOTO_VML_WIDTH_PT}pt;z-index:{PHOTO_VML_Z_INDEX};"
        "mso-width-relative:page;mso-height-relative:page;"
    )


def _embed_image_rid(paragraph: Paragraph, image_path: str) -> str:
    image = Image.from_file(image_path)
    _, rid = paragraph.part.get_or_add_image(image)
    return rid


def _hint_textbox_xml(hint_text: str) -> str:
    safe = html.escape(hint_text, quote=False)
    return f"""
      <v:textbox>
        <w:txbxContent>
          <w:p>
            <w:pPr>
              <w:ind w:left="-142" w:right="-119"/>
              <w:jc w:val="center"/>
              <w:rPr><w:sz w:val="20"/><w:szCs w:val="21"/></w:rPr>
            </w:pPr>
            <w:r>
              <w:rPr><w:sz w:val="20"/><w:szCs w:val="21"/></w:rPr>
              <w:t xml:space="preserve">{safe}</w:t>
            </w:r>
          </w:p>
        </w:txbxContent>
      </v:textbox>
    """


def _append_vml_rect(run, *, rid: str | None = None, hint_text: str | None = None) -> None:
    spid = _next_spid()
    style = html.escape(_vml_rect_style(), quote=True)
    if rid:
        inner = f"""
          <v:path/>
          <v:fill r:id="{rid}" type="frame"/>
          <v:stroke/>
          <v:imagedata r:id="{rid}" o:title=""/>
          <o:lock v:ext="edit"/>
        """
    else:
        hint_box = _hint_textbox_xml(hint_text or " ") if hint_text else ""
        inner = f"""
          <v:path/>
          <v:fill focussize="0,0"/>
          <v:stroke/>
          <v:imagedata o:title=""/>
          <o:lock v:ext="edit"/>
          {hint_box}
        """

    pict_xml = f"""
    <w:pict
      xmlns:w="{W_NS}"
      xmlns:v="{V_NS}"
      xmlns:o="{O_NS}"
      xmlns:r="{R_NS}">
      <v:rect id="{spid}" o:spid="{spid}" o:spt="1"
        style="{style}" coordsize="21600,21600">
        {inner}
      </v:rect>
    </w:pict>
    """
    run._r.append(parse_xml(pict_xml))


def add_vml_photo(
    paragraph: Paragraph,
    image_path: str | None,
    *,
    hint_text: str = "",
) -> None:
    """Namuna kabi v:rect (VML pict) — foto yoki matnli placeholder."""
    run = paragraph.add_run()
    if image_path:
        rid = _embed_image_rid(paragraph, image_path)
        _append_vml_rect(run, rid=rid)
    else:
        _append_vml_rect(run, hint_text=hint_text)
