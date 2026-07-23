"""Credit packages and paywall pricing helpers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config.settings import settings


@dataclass(frozen=True)
class CreditPackage:
    id: str
    credits: int
    price_uzs: int
    label: str
    per_unit_uzs: int
    badge: str = ""


def _packages() -> tuple[CreditPackage, ...]:
    p1 = int(getattr(settings, "package_1_price_uzs", None) or settings.single_doc_price_uzs or 7999)
    p3 = int(getattr(settings, "package_3_price_uzs", None) or 14_999)
    p5 = int(getattr(settings, "package_5_price_uzs", None) or 19_999)
    return (
        CreditPackage("pack1", 1, p1, "1 hujjat", p1, ""),
        CreditPackage("pack3", 3, p3, "3 hujjat", p3 // 3, "⭐ eng ommabop"),
        CreditPackage("pack5", 5, p5, "5 hujjat", p5 // 5, "🔥 eng arzon"),
    )


def list_packages() -> list[dict[str, Any]]:
    return [
        {
            "id": p.id,
            "credits": p.credits,
            "price_uzs": p.price_uzs,
            "label": p.label,
            "per_unit_uzs": p.per_unit_uzs,
            "badge": p.badge,
        }
        for p in _packages()
    ]


def get_package(package_id: str | None) -> CreditPackage:
    pid = (package_id or "pack1").strip().lower()
    for p in _packages():
        if p.id == pid:
            return p
    return _packages()[0]


def package_from_amount(amount: int | None) -> CreditPackage:
    """Best-effort map stored payment amount → package (legacy rows default to 1)."""
    try:
        amt = int(amount or 0)
    except (TypeError, ValueError):
        amt = 0
    for p in reversed(_packages()):
        if amt >= p.price_uzs:
            return p
    return _packages()[0]


def format_uzs(amount: int) -> str:
    return f"{int(amount):,}".replace(",", " ")


def packages_block_text() -> str:
    lines = ["💰 <b>Paketlar:</b>"]
    for p in _packages():
        badge = f" — <i>{p.badge}</i>" if p.badge else ""
        lines.append(
            f"• <b>{p.credits}×</b> = <b>{format_uzs(p.price_uzs)} so'm</b> "
            f"(~{format_uzs(p.per_unit_uzs)}/dona){badge}"
        )
    return "\n".join(lines)


def soft_paywall_text(*, promo_active: bool = False, promo_hours_left: int | None = None) -> str:
    """Yumshoq sotuv — to'siq emas."""
    lines = [
        "✨ <b>Hujjatingiz tayyor!</b>",
        "",
        "📄 <b>Demo (belgili)</b> — bepul ko'rish/tekshirish uchun.",
        "💎 <b>Toza fayl</b> (watermarksiz) — paketdan birini tanlang:",
        "",
        packages_block_text(),
    ]
    if promo_active:
        left = ""
        if promo_hours_left is not None and promo_hours_left > 0:
            left = f" ({promo_hours_left} soat qoldi)"
        lines.extend(
            [
                "",
                f"⚡️ <b>Bugun to'lasangiz:</b> +1 Muqova xati bepul{left}!",
            ]
        )
    lines.extend(
        [
            "",
            "👇 Paketni tanlang — to'lov 1–2 daqiqada tasdiqlanadi.",
        ]
    )
    return "\n".join(lines)
