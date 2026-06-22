"""Uzbek Latin ↔ Cyrillic transliteration (WebApp /api/translit legacy)."""
from __future__ import annotations

from dataclasses import dataclass

_LATIN_TO_CYR_MAP = {
    "A": "А", "a": "а", "B": "Б", "b": "б", "D": "Д", "d": "д",
    "E": "Е", "e": "е", "F": "Ф", "f": "ф", "G": "Г", "g": "г",
    "H": "Ҳ", "h": "ҳ", "I": "И", "i": "и", "J": "Ж", "j": "ж",
    "K": "К", "k": "к", "L": "Л", "l": "л", "M": "М", "m": "м",
    "N": "Н", "n": "н", "O": "О", "o": "о", "P": "П", "p": "п",
    "Q": "Қ", "q": "қ", "R": "Р", "r": "р", "S": "С", "s": "с",
    "T": "Т", "t": "т", "U": "У", "u": "у", "V": "В", "v": "в",
    "X": "Х", "x": "х", "Y": "Й", "y": "й", "Z": "З", "z": "з",
    "Oʻ": "Ў", "oʻ": "ў", "Gʻ": "Ғ", "gʻ": "ғ",
    "Sh": "Ш", "sh": "ш", "Ch": "Ч", "ch": "ч", "Ng": "Нг", "ng": "нг",
}

_CYR_TO_LATIN = {
    "А": "A", "а": "a", "Б": "B", "б": "b", "В": "V", "в": "v",
    "Г": "G", "г": "g", "Д": "D", "д": "d", "Е": "E", "е": "e",
    "Ё": "Yo", "ё": "yo", "Ж": "J", "ж": "j", "З": "Z", "з": "z",
    "И": "I", "и": "i", "Й": "Y", "й": "y", "К": "K", "к": "k",
    "Л": "L", "л": "l", "М": "M", "м": "m", "Н": "N", "н": "n",
    "О": "O", "о": "o", "П": "P", "п": "p", "Р": "R", "р": "r",
    "С": "S", "с": "s", "Т": "T", "т": "t", "У": "U", "у": "u",
    "Ф": "F", "ф": "f", "Х": "X", "х": "x", "Ц": "Ts", "ц": "ts",
    "Ч": "Ch", "ч": "ch", "Ш": "Sh", "ш": "sh", "Щ": "Sh", "щ": "sh",
    "Ъ": "", "ъ": "", "Ь": "", "ь": "", "Э": "E", "э": "e",
    "Ю": "Yu", "ю": "yu", "Я": "Ya", "я": "ya",
    "Ў": "Oʻ", "ў": "oʻ", "Ғ": "Gʻ", "ғ": "gʻ", "Қ": "Q", "қ": "q",
    "Ҳ": "H", "ҳ": "h",
}


@dataclass(frozen=True)
class TransliterationResult:
    result: str
    direction: str  # lotin_to_krill | krill_to_lotin | none


def _has_cyrillic(text: str) -> bool:
    return any("\u0400" <= ch <= "\u04FF" for ch in text)


def _has_latin(text: str) -> bool:
    return any(ch.isalpha() and ord(ch) < 128 for ch in text)


def _latin_to_cyrillic(text: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(text):
        matched = False
        for size in (2, 1):
            chunk = text[i : i + size]
            if chunk in _LATIN_TO_CYR_MAP:
                out.append(_LATIN_TO_CYR_MAP[chunk])
                i += size
                matched = True
                break
        if not matched:
            out.append(text[i])
            i += 1
    return "".join(out)


def _cyrillic_to_latin(text: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(text):
        two = text[i : i + 2]
        if two in _CYR_TO_LATIN:
            out.append(_CYR_TO_LATIN[two])
            i += 2
            continue
        ch = text[i]
        out.append(_CYR_TO_LATIN.get(ch, ch))
        i += 1
    return "".join(out)


def auto_cyrillic_latin(text: str) -> TransliterationResult:
    """Detect script and transliterate Uzbek text."""
    raw = (text or "").strip()
    if not raw:
        return TransliterationResult(result="", direction="none")

    if _has_cyrillic(raw) and not _has_latin(raw):
        return TransliterationResult(result=_cyrillic_to_latin(raw), direction="krill_to_lotin")

    if _has_latin(raw) and not _has_cyrillic(raw):
        return TransliterationResult(result=_latin_to_cyrillic(raw), direction="lotin_to_krill")

    return TransliterationResult(result=raw, direction="none")
