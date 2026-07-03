"""Mahalliy tarjima — AI o'rniga aniq iboralar (obyektivka)."""
from __future__ import annotations

import re

_AWARD_PATTERNS_EN = (
    (re.compile(r'"?mehnat\s+shuhrati"?', re.I), '"Labor Glory" order'),
    (re.compile(r'"?shuhrat"?', re.I), '"Glory" medal'),
    (re.compile(r'"?do\'?stlik"?', re.I), '"Friendship" order'),
    (re.compile(r'"?fidokorlik"?', re.I), '"Devotion" order'),
    (re.compile(r"mustaqillik\s+ordeni", re.I), "Independence order"),
    (re.compile(r'"?sog\'?liq"?', re.I), '"Health" order'),
    (re.compile(r"медал", re.I), "medal"),
    (re.compile(r"орден", re.I), "order"),
    (re.compile(r"\bй\.?\b", re.I), ""),
    (re.compile(r"\s{2,}"), " "),
)

_AWARD_PATTERNS_RU = (
    (re.compile(r'"?mehnat\s+shuhrati"?', re.I), 'орден "Трудовой славы"'),
    (re.compile(r'"?mehnat\s+shuhra?ti"?', re.I), 'орден "Трудовой славы"'),
    (re.compile(r'"?shuhrat"?', re.I), 'медаль "Слава"'),
    (re.compile(r'"?shuhra?ti"?', re.I), 'медаль "Слава"'),
    (re.compile(r'"?do\'?stlik"?', re.I), 'орден "Дружбы"'),
    (re.compile(r'"?fidokorlik"?', re.I), 'орден "Почёта"'),
    (re.compile(r"mustaqillik\s+ordeni", re.I), 'орден "Независимости"'),
    (re.compile(r'"?sog\'?liq"?', re.I), 'орден "Здоровье"'),
    (re.compile(r"\bй\.?\b"), "г."),
    (re.compile(r"\s{2,}"), " "),
)

_BIRTH_YEAR_RE = re.compile(
    r"^(\d{4})\s*(?:"
    r"(?:-)?yil(?:da|dan)?|"
    r"(?:-)?йил(?:да|дан)?|"
    r"(?:-)?yilda|(?:-)?йилида|"
    r"-?y\.?|-?й\.?"
    r")?\s*$",
    re.IGNORECASE,
)

_RELATIONSHIP_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "otasi": "Father",
        "onasi": "Mother",
        "opasi": "Elder sister",
        "singlisi": "Younger sister",
        "akasi": "Elder brother",
        "ukasi": "Younger brother",
        "turmush ortog'i": "Spouse",
        "xotini": "Wife",
        "eri": "Husband",
        "o'g'li": "Son",
        "qizi": "Daughter",
        "qaynotasi": "Father-in-law",
        "qaynonasi": "Mother-in-law",
    },
    "ru": {
        "otasi": "Отец",
        "onasi": "Мать",
        "opasi": "Старшая сестра",
        "singlisi": "Младшая сестра",
        "akasi": "Старший брат",
        "ukasi": "Младший брат",
        "turmush ortog'i": "Супруг(а)",
        "xotini": "Жена",
        "eri": "Муж",
        "o'g'li": "Сын",
        "qizi": "Дочь",
        "qaynotasi": "Свекор",
        "qaynonasi": "Свекровь",
    },
}


def relationship_label(degree: str, lang: str) -> str:
    raw = (degree or "").strip()
    if not raw:
        return raw
    key = raw.lower().replace("ʻ", "'").replace("'", "'")
    lang_key = "en" if (lang or "").strip().lower() == "en" else "ru" if (lang or "").strip().lower() == "ru" else ""
    if lang_key:
        mapped = _RELATIONSHIP_LABELS.get(lang_key, {}).get(key)
        if mapped:
            return mapped
    return raw


def format_birth_year_place(text: str, direction: str) -> str | None:
    raw = (text or "").strip()
    if not raw:
        return None
    m = _BIRTH_YEAR_RE.match(raw.replace(" ", ""))
    if not m and re.fullmatch(r"\d{4}", raw):
        m = re.match(r"^(\d{4})$", raw)
    if not m:
        return None
    year = m.group(1)
    if direction == "uz_en":
        return f"In {year}"
    if direction == "uz_ru":
        return f"В {year} году"
    return None


def translate_awards_phrase(text: str, direction: str) -> str | None:
    raw = (text or "").strip()
    if not raw:
        return None
    low = raw.lower()
    if low in ("yo'q", "йўқ", "yoq", "нет", "none", "no"):
        return None

    patterns = _AWARD_PATTERNS_EN if direction == "uz_en" else _AWARD_PATTERNS_RU
    out = raw
    if re.search(r"[\u0400-\u04ff]", raw):
        normalized = (
            raw.replace("ҳ", "х")
            .replace("Ҳ", "Х")
            .replace("ў", "у")
            .replace("Ў", "У")
            .replace("қ", "к")
            .replace("Қ", "К")
            .replace("ғ", "г")
            .replace("Ғ", "Г")
        )
        cyr_map = {
            "шухрати": '"Glory" medal' if direction == "uz_en" else 'медаль "Слава"',
            "шухрат": '"Glory" medal' if direction == "uz_en" else 'медаль "Слава"',
            "меҳнат шуҳрати": '"Labor Glory" order' if direction == "uz_en" else 'орден "Трудовой славы"',
            "меҳнат шухрати": '"Labor Glory" order' if direction == "uz_en" else 'орден "Трудовой славы"',
            "медал": "medal" if direction == "uz_en" else "медаль",
            "ордени": "order" if direction == "uz_en" else "орден",
            "орден": "order" if direction == "uz_en" else "орден",
            "й.": "" if direction == "uz_en" else "г.",
            "йил": "" if direction == "uz_en" else "г.",
        }
        for source_text in (raw, normalized):
            work = source_text
            for old, new in cyr_map.items():
                work = re.sub(re.escape(old), new, work, flags=re.IGNORECASE)
            for pattern, repl in patterns:
                work = pattern.sub(repl, work)
            work = re.sub(r"\s*,\s*", ", ", work).strip(" ,.")
            work = re.sub(r"\s{2,}", " ", work)
            if work and work != raw:
                out = work
                break
    for pattern, repl in patterns:
        out = pattern.sub(repl, out)
    out = re.sub(r"\s*,\s*", ", ", out).strip(" ,.")
    out = re.sub(r"\s{2,}", " ", out)
    if out and out != raw:
        return out
    if direction == "uz_en" and re.search(r"[\u0400-\u04ff]", raw):
        return None
    return None
