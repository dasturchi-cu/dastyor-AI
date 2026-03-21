"""Normalize Gemini HTML OCR output to plain text (shared by OCR endpoints)."""
from __future__ import annotations

import html as html_lib
import re


def html_ocr_to_plain(html_text: str) -> str:
    text = html_text or ""
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|h1|h2|h3|h4|h5|h6|tr|li|ul|ol|table)>", "\n", text)
    text = re.sub(r"(?i)<td[^>]*>", "\t", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_lib.unescape(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
