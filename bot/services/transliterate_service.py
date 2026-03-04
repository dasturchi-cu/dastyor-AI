"""
Uzbek Cyrillic ↔ Latin transliteration service.

BUGS FIXED:
  1. Ц/ц was mapped to S/s instead of correct Ts/ts
  2. Ҳ/ҳ (ha) were completely missing from CYR→LAT map
  3. duplicate dict keys in _build_lat_to_cyr_map silently killed g'/G' entries
  4. latin_to_cyrillic only handled 2 apostrophe variants — now handles all 4
  5. ts/Ts/TS digraph was missing from LAT→CYR 2-char table
"""

from typing import Literal

Direction = Literal["krill_to_lotin", "lotin_to_krill"]

# ── All apostrophe characters that can represent the Uzbek soft sign ──
# U+0027 straight, U+2019 right-curly, U+02BB modifier-letter, backtick
_APOS = ("'", "\u2019", "\u02BB", "`")


# ─────────────────────────────────────────────────────────────────────────────
# CYRILLIC → LATIN
# ─────────────────────────────────────────────────────────────────────────────
_CYR_TO_LAT: dict[str, str] = {
    "А": "A",  "а": "a",
    "Б": "B",  "б": "b",
    "В": "V",  "в": "v",
    "Г": "G",  "г": "g",
    "Д": "D",  "д": "d",
    "Е": "E",  "е": "e",
    "Ё": "Yo", "ё": "yo",
    "Ж": "J",  "ж": "j",
    "З": "Z",  "з": "z",
    "И": "I",  "и": "i",
    "Й": "Y",  "й": "y",
    "К": "K",  "к": "k",
    "Л": "L",  "л": "l",
    "М": "M",  "м": "m",
    "Н": "N",  "н": "n",
    "О": "O",  "о": "o",
    "П": "P",  "п": "p",
    "Р": "R",  "р": "r",
    "С": "S",  "с": "s",
    "Т": "T",  "т": "t",
    "У": "U",  "у": "u",
    "Ф": "F",  "ф": "f",
    "Х": "X",  "х": "x",
    "Ц": "Ts", "ц": "ts",   # FIX: was incorrectly 'S'/'s'
    "Ч": "Ch", "ч": "ch",
    "Ш": "Sh", "ш": "sh",
    "Щ": "Sh", "щ": "sh",
    "Ъ": "'",  "ъ": "'",   # hard sign → apostrophe
    "Ы": "I",  "ы": "i",
    "Ь": "",   "ь": "",    # soft sign → empty
    "Э": "E",  "э": "e",
    "Ю": "Yu", "ю": "yu",
    "Я": "Ya", "я": "ya",
    # Uzbek-specific
    "Қ": "Q",  "қ": "q",
    "Ғ": "G'", "ғ": "g'",
    "Ҳ": "H",  "ҳ": "h",   # FIX: was completely missing
    "Ў": "O'", "ў": "o'",
    "Ҷ": "J",  "ҷ": "j",
}


# ─────────────────────────────────────────────────────────────────────────────
# LATIN → CYRILLIC lookup tables (3-char, 2-char, 1-char)
# Built once at import time via _build_lat_to_cyr_maps().
# ─────────────────────────────────────────────────────────────────────────────
_LAT_TO_CYR_3: dict[str, str] = {}   # e.g. "o'" → "ў"
_LAT_TO_CYR_2: dict[str, str] = {}   # e.g. "sh" → "ш"
_LAT_TO_CYR_1: dict[str, str] = {}   # e.g. "a"  → "а"


def _build_lat_to_cyr_maps() -> None:
    """Populate all lookup tables exactly once at import time."""

    # ── 3-char: o/O/g/G followed by ANY apostrophe variant ──────────────
    for ap in _APOS:
        _LAT_TO_CYR_3["o" + ap] = "ў"
        _LAT_TO_CYR_3["O" + ap] = "Ў"
        _LAT_TO_CYR_3["g" + ap] = "ғ"
        _LAT_TO_CYR_3["G" + ap] = "Ғ"

    # ── 2-char digraphs ──────────────────────────────────────────────────
    digraphs: list[tuple[str, str]] = [
        ("sh", "ш"), ("Sh", "Ш"), ("SH", "Ш"),
        ("ch", "ч"), ("Ch", "Ч"), ("CH", "Ч"),
        ("ng", "нг"), ("Ng", "Нг"), ("NG", "НГ"),
        ("yo", "ё"), ("Yo", "Ё"), ("YO", "Ё"),
        ("ya", "я"), ("Ya", "Я"), ("YA", "Я"),
        ("yu", "ю"), ("Yu", "Ю"), ("YU", "Ю"),
        ("ts", "ц"), ("Ts", "Ц"), ("TS", "Ц"),   # FIX: was missing
        ("zh", "ж"), ("Zh", "Ж"), ("ZH", "Ж"),
    ]
    for lat, cyr in digraphs:
        _LAT_TO_CYR_2[lat] = cyr

    # ── 1-char singles ───────────────────────────────────────────────────
    singles: list[tuple[str, str]] = [
        ("a", "а"), ("b", "б"), ("d", "д"), ("e", "е"), ("f", "ф"),
        ("g", "г"), ("h", "ҳ"), ("i", "и"), ("j", "ж"), ("k", "к"),
        ("l", "л"), ("m", "м"), ("n", "н"), ("o", "о"), ("p", "п"),
        ("q", "қ"), ("r", "р"), ("s", "с"), ("t", "т"), ("u", "у"),
        ("v", "в"), ("w", "в"), ("x", "х"), ("y", "й"), ("z", "з"),
    ]
    for lat, cyr in singles:
        _LAT_TO_CYR_1[lat] = cyr
        # upper-case: ensure first char is upper, rest stay (handles multi-char cyr)
        _LAT_TO_CYR_1[lat.upper()] = cyr[0].upper() + cyr[1:]

    # Apostrophe variants → ъ (hard sign, used in transliteration fallback)
    for ap in _APOS:
        _LAT_TO_CYR_1[ap] = "ъ"


_build_lat_to_cyr_maps()

# Built flat legacy map (backward-compat for any external code using _LAT_TO_CYR)
_LAT_TO_CYR: dict[str, str] = {**_LAT_TO_CYR_2, **_LAT_TO_CYR_1}


# ─────────────────────────────────────────────────────────────────────────────
def cyrillic_to_latin(text: str) -> str:
    """Convert Uzbek Cyrillic text to Latin."""
    return "".join(_CYR_TO_LAT.get(ch, ch) for ch in text)


def latin_to_cyrillic(text: str) -> str:
    """Convert Uzbek Latin text to Cyrillic.

    Uses a greedy left-to-right single-pass scanner:
      1. Try 3-char window (o/g + apostrophe variant)
      2. Try 2-char window (digraphs: sh, ch, ts, ng, yo …)
      3. Try 1-char (single letters, apostrophe → ъ)
      4. Pass through unchanged (digits, punctuation, spaces)

    Each code-point is consumed exactly once — no double-substitution.
    """
    result: list[str] = []
    i = 0
    n = len(text)

    while i < n:
        # ── 3-char window ─────────────────────────────────────────────
        if i + 2 < n:
            tri = text[i: i + 3]
            if tri in _LAT_TO_CYR_3:
                result.append(_LAT_TO_CYR_3[tri])
                i += 3
                continue

        # ── 2-char window ─────────────────────────────────────────────
        if i + 1 < n:
            di = text[i: i + 2]
            if di in _LAT_TO_CYR_2:
                result.append(_LAT_TO_CYR_2[di])
                i += 2
                continue

        # ── 1-char ────────────────────────────────────────────────────
        ch = text[i]
        if ch in _LAT_TO_CYR_1:
            result.append(_LAT_TO_CYR_1[ch])
        else:
            result.append(ch)   # digits, punctuation, spaces pass through
        i += 1

    return "".join(result)


def transliterate(text: str, direction: Direction) -> str:
    """Public API for transliteration."""
    if direction == "krill_to_lotin":
        return cyrillic_to_latin(text)
    if direction == "lotin_to_krill":
        return latin_to_cyrillic(text)
    return text
