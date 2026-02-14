"""
Uzbek Cyrillic ↔ Latin transliteration service.

Implements official Uzbek alphabet rules for basic text transliteration.
This is a pure text-based implementation and does not handle DOCX/PPTX/XLSX
internals yet – handlers can use it for message-level conversions.
"""

from typing import Literal

Direction = Literal["krill_to_lotin", "lotin_to_krill"]


# Mapping for single Cyrillic letters to Latin
_CYR_TO_LAT = {
    "А": "A", "а": "a",
    "Б": "B", "б": "b",
    "В": "V", "в": "v",
    "Г": "G", "г": "g",
    "Д": "D", "д": "d",
    "Е": "E", "е": "e",
    "Ё": "Yo", "ё": "yo",
    "Ж": "J", "ж": "j",
    "З": "Z", "з": "z",
    "И": "I", "и": "i",
    "Й": "Y", "й": "y",
    "К": "K", "к": "k",
    "Л": "L", "л": "l",
    "М": "M", "м": "m",
    "Н": "N", "н": "n",
    "О": "O", "о": "o",
    "П": "P", "п": "p",
    "Р": "R", "р": "r",
    "С": "S", "с": "s",
    "Т": "T", "т": "t",
    "У": "U", "у": "u",
    "Ф": "F", "ф": "f",
    "Х": "X", "х": "x",
    "Ц": "S", "ц": "s",  # odatda "s"
    "Ч": "Ch", "ч": "ch",
    "Ш": "Sh", "ш": "sh",
    "Щ": "Sh", "щ": "sh",  # juda kam ishlatiladi
    "Ъ": "", "ъ": "",
    "Ы": "I", "ы": "i",
    "Ь": "", "ь": "",
    "Э": "E", "э": "e",
    "Ю": "Yu", "ю": "yu",
    "Я": "Ya", "я": "ya",
    "Қ": "Q", "қ": "q",
    "Ғ": "G‘", "ғ": "g‘",
    "Ў": "O‘", "ў": "o‘",
}


def _build_lat_to_cyr_map() -> dict[str, str]:
    """
    Build Latin → Cyrillic map suitable for Uzbek.
    We handle digraphs like sh, ch, ng, o‘, g‘ first.
    """
    mapping: dict[str, str] = {
        "sh": "ш",
        "Sh": "Ш",
        "SH": "Ш",
        "ch": "ч",
        "Ch": "Ч",
        "CH": "Ч",
        "ng": "нг",  # approximate
        "Ng": "Нг",
        "NG": "НГ",
        "yo": "ё",
        "Yo": "Ё",
        "YO": "Ё",
        "yu": "ю",
        "Yu": "Ю",
        "YU": "Ю",
        "ya": "я",
        "Ya": "Я",
        "YA": "Я",
        "o‘": "ў",
        "O‘": "Ў",
        "g‘": "ғ",
        "G‘": "Ғ",
        "o'": "ў",  # fallback with regular apostrophe
        "O'": "Ў",
        "g'": "ғ",
        "G'": "Ғ",
    }

    # Single letters
    single_pairs = {
        "a": "а",
        "b": "б",
        "d": "д",
        "e": "е",
        "f": "ф",
        "g": "г",
        "h": "ҳ",  # note: Latin h -> Cyrillic ҳ
        "i": "и",
        "j": "ж",
        "k": "к",
        "l": "л",
        "m": "м",
        "n": "н",
        "o": "о",
        "p": "п",
        "q": "қ",
        "r": "р",
        "s": "с",
        "t": "т",
        "u": "у",
        "v": "в",
        "x": "х",
        "y": "й",
        "z": "з",
    }

    for lat, cyr in single_pairs.items():
        mapping[lat] = cyr
        mapping[lat.upper()] = cyr.upper()

    return mapping


_LAT_TO_CYR = _build_lat_to_cyr_map()


def cyrillic_to_latin(text: str) -> str:
    """Convert Uzbek Cyrillic text to Latin."""
    return "".join(_CYR_TO_LAT.get(ch, ch) for ch in text)


def latin_to_cyrillic(text: str) -> str:
    """Convert Uzbek Latin text to Cyrillic (basic heuristic implementation)."""
    result: list[str] = []
    i = 0
    length = len(text)

    while i < length:
        # Try digraphs / special sequences (up to 2 chars, including apostrophe variants)
        if i + 1 < length:
            pair = text[i : i + 2]
            triple = None

            # Handle o‘ / g‘ variants (3 chars with combining apostrophe)
            if i + 2 < length and text[i + 1] in ("'", "‘") and text[i] in ("o", "O", "g", "G"):
                triple = text[i : i + 3]

            if triple and triple in _LAT_TO_CYR:
                result.append(_LAT_TO_CYR[triple])
                i += 3
                continue

            if pair in _LAT_TO_CYR:
                result.append(_LAT_TO_CYR[pair])
                i += 2
                continue

        ch = text[i]
        if ch in _LAT_TO_CYR:
            result.append(_LAT_TO_CYR[ch])
        else:
            result.append(ch)
        i += 1

    return "".join(result)


def transliterate(text: str, direction: Direction) -> str:
    """Public API for transliteration."""
    if direction == "krill_to_lotin":
        return cyrillic_to_latin(text)
    if direction == "lotin_to_krill":
        return latin_to_cyrillic(text)
    return text


