from __future__ import annotations

from dataclasses import dataclass

from bot.services.transliterate_service import cyrillic_to_latin, latin_to_cyrillic


@dataclass(frozen=True)
class AutoScriptResult:
    detected: str  # "latin" | "cyrillic" | "unknown"
    direction: str  # "lotin_to_krill" | "krill_to_lotin" | "none"
    result: str
    stats: dict


def _is_cyrillic(ch: str) -> bool:
    o = ord(ch)
    # Cyrillic + Cyrillic supplement blocks
    return (0x0400 <= o <= 0x04FF) or (0x0500 <= o <= 0x052F)


def _is_latin_letter(ch: str) -> bool:
    # Fast path: ASCII
    if "A" <= ch <= "Z" or "a" <= ch <= "z":
        return True
    # Common Uzbek latin extensions
    return ch in ("ʻ", "ʼ", "’", "`", "'")


def auto_cyrillic_latin(text: str) -> AutoScriptResult:
    """
    STRICT logic:
      - Latin dominates  -> convert to Cyrillic
      - Cyrillic dominates -> convert to Latin
      - If neither dominates -> return original (direction=none)
    """
    s = text or ""
    cyr = 0
    lat = 0
    letters = 0
    for ch in s:
        if ch.isalpha() or _is_cyrillic(ch) or _is_latin_letter(ch):
            # Count "letter-like" only to avoid punctuation bias.
            if _is_cyrillic(ch):
                cyr += 1
                letters += 1
            elif ch.isalpha() or _is_latin_letter(ch):
                # isalpha includes Cyrillic too, but Cyrillic handled above.
                lat += 1
                letters += 1

    stats = {"latin": lat, "cyrillic": cyr, "letters": letters}

    if lat > cyr and lat >= 2:
        out = latin_to_cyrillic(s)
        return AutoScriptResult(
            detected="latin",
            direction="lotin_to_krill",
            result=out,
            stats=stats,
        )
    if cyr > lat and cyr >= 2:
        out = cyrillic_to_latin(s)
        return AutoScriptResult(
            detected="cyrillic",
            direction="krill_to_lotin",
            result=out,
            stats=stats,
        )
    return AutoScriptResult(
        detected="unknown",
        direction="none",
        result=s,
        stats=stats,
    )

