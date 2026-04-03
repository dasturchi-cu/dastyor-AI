import os
from datetime import datetime, timezone


STANDARD_PRICE_UZS = int(os.getenv("STANDARD_PRICE_UZS", "9999") or "9999")
PREMIUM_PRICE_UZS = int(os.getenv("PREMIUM_PRICE_UZS", "29999") or "29999")
# CV / obyektivka (bitta hujjat) — premium EMAS
SINGLE_DOC_PRICE_UZS = int(os.getenv("SINGLE_DOC_PRICE_UZS", "5000") or "5000")

# Referral discount (standard + premium)
REFERRAL_REQUIRED_INVITES = int(os.getenv("REFERRAL_REQUIRED_INVITES", "5") or "5")
REFERRAL_DISCOUNT_PERCENT = int(os.getenv("REFERRAL_DISCOUNT_PERCENT", "30") or "30")

# Marketing promo copy
PROMO_LABEL = (os.getenv("PROMO_LABEL", "Start promo") or "Start promo").strip()
PROMO_DEADLINE_ISO = (os.getenv("PROMO_DEADLINE_ISO", "") or "").strip()


def promo_deadline_display() -> str | None:
    """
    Returns YYYY-MM-DD if PROMO_DEADLINE_ISO parses, else None.
    """
    if not PROMO_DEADLINE_ISO:
        return None
    try:
        s = PROMO_DEADLINE_ISO.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.date().isoformat()
    except Exception:
        # If user sets PROMO_DEADLINE_ISO=2026-03-31 also works
        try:
            return str(PROMO_DEADLINE_ISO)[:10]
        except Exception:
            return None


def format_uzs(n: int) -> str:
    s = str(int(n))
    # 29999 -> 29 999
    return " ".join([s[max(i - 3, 0):i] for i in range(len(s), 0, -3)][::-1])


def apply_percent_discount(amount: int, percent: int) -> int:
    p = max(0, min(100, int(percent)))
    return int(round(amount * (100 - p) / 100.0))
