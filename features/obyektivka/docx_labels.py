"""Replace fixed Uzbek/Cyrillic DOCX labels when exporting en/ru documents."""

from __future__ import annotations

from lxml import etree

from features.obyektivka.docx_typography import W
from features.obyektivka.layout import OB_LABELS

_REL_ROW_LABELS: dict[str, list[tuple[str, str]]] = {
    "en": [
        ("Отаси", "Father"),
        ("Онаси", "Mother"),
        ("Опаси", "Elder sister"),
        ("Синглиси", "Younger sister"),
        ("Укаси", "Brother"),
        ("Турмуш ўртоғи", "Spouse"),
        ("Ўғли", "Son"),
        ("Қизи", "Daughter"),
        ("Қайнотаси", "Father-in-law"),
        ("Қайнонаси", "Mother-in-law"),
        ("Otasi", "Father"),
        ("Onasi", "Mother"),
        ("Opasi", "Elder sister"),
        ("Singlisi", "Younger sister"),
        ("Ukasi", "Brother"),
    ],
    "ru": [
        ("Отаси", "Отец"),
        ("Онаси", "Мать"),
        ("Опаси", "Старшая сестра"),
        ("Синглиси", "Младшая сестра"),
        ("Укаси", "Брат"),
        ("Турмуш ўртоғи", "Супруг(а)"),
        ("Ўғли", "Сын"),
        ("Қизи", "Дочь"),
        ("Қайнотаси", "Свекор"),
        ("Қайнонаси", "Свекровь"),
    ],
}

_EXTRA_PAIRS: dict[str, list[tuple[str, str]]] = {
    "en": [
        ("Қариндошлиги", "Relationship"),
        ("Фамилияси, исми ва отасининг исми", "Surname, Name and Patronymic"),
        ("Фамилияси, исми, отасининг исми", "Surname, Name and Patronymic"),
        ("қариндош-лиги", "Relationship"),
        ("қариндошлиги", "Relationship"),
        ("Қариндош-лиги", "Relationship"),
        ("Туғилган йили ва жойи", "Year and place of birth"),
        ("Year of birth ва жойи", "Year and place of birth"),
        (" ва жойи", " and place of birth"),
    ],
    "ru": [
        ("Фамилияси, исми ва отасининг исми", "Фамилия, имя и отчество"),
        ("Фамилияси, исми, отасининг исми", "Фамилия, имя и отчество"),
        ("қариндош-лиги", "Степень родства"),
        ("қариндошлиги", "Степень родства"),
        ("Қариндош-лиги", "Степень родства"),
        ("Year of birth ва жойи", "Год и место рождения"),
        (" ва жойи", " и место рождения"),
    ],
}


def _replacement_pairs(target_lang: str) -> list[tuple[str, str]]:
    lang = (target_lang or "").strip().lower()
    if lang not in ("en", "ru"):
        return []

    src = OB_LABELS.get("uz_cyr", {})
    tgt = OB_LABELS.get(lang, {})
    pairs: list[tuple[str, str]] = []
    for key, old in src.items():
        new = tgt.get(key)
        if old and new and old != new:
            pairs.append((old, new))

    pairs.extend(_EXTRA_PAIRS.get(lang, []))
    pairs.extend(_REL_ROW_LABELS.get(lang, []))

    src_lat = OB_LABELS.get("uz_lat", {})
    for key, old in src_lat.items():
        new = tgt.get(key)
        if old and new and old != new and (old, new) not in pairs:
            pairs.append((old, new))

    pairs.sort(key=lambda item: len(item[0]), reverse=True)
    return pairs


def _apply_pairs(text: str, pairs: list[tuple[str, str]]) -> str:
    updated = text
    for old, new in pairs:
        if old in updated:
            updated = updated.replace(old, new)
    return updated


def _paragraph_text(p_el: etree._Element) -> str:
    return "".join(t.text or "" for t in p_el.findall(f".//{W}t"))


def _set_paragraph_text(p_el: etree._Element, text: str) -> None:
    runs = p_el.findall(f".//{W}r")
    if not runs:
        return
    text_nodes = [t for r in runs for t in r.findall(f"{W}t")]
    if not text_nodes:
        return
    text_nodes[0].text = text
    for node in text_nodes[1:]:
        node.text = ""


def apply_document_labels(root: etree._Element, lang: str) -> None:
    pairs = _replacement_pairs(lang)
    if not pairs:
        return

    for p_el in root.findall(f".//{W}p"):
        text = _paragraph_text(p_el)
        if not text.strip():
            continue
        updated = _apply_pairs(text, pairs)
        if updated != text:
            _set_paragraph_text(p_el, updated)
