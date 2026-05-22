"""Foydalanuvchi hujjatlari — paid_doc_requests ko‘rinishi."""
from __future__ import annotations

from bot.services.bot_notify import paid_doc_status_label
from bot.services.supabase_db import (
    db_get_user,
    db_list_user_paid_doc_requests,
    has_db,
    normalize_paid_doc_status,
)


def _compact_doc_rows(rows: list[dict]) -> list[dict]:
    """Eski takroriy «pending» yozuvlarni yashirish — faqat oxirgi holatlar."""
    out: list[dict] = []
    seen_pending_kind: set[str] = set()
    for r in rows:
        kind = str(r.get("kind") or "").strip().lower()
        try:
            st = normalize_paid_doc_status(str(r.get("status") or "pending"))
        except Exception:
            st = "pending"
        if st == "pending" and kind in seen_pending_kind:
            continue
        if st == "pending":
            seen_pending_kind.add(kind)
        out.append(r)
        if len(out) >= 4:
            break
    return out


def format_my_documents_text(user_id: int) -> str:
    uid = int(user_id)
    lines = ["📂 <b>Mening hujjatlarim</b>\n"]

    if not has_db():
        lines.append("⚠️ Ma’lumotlar bazasi ulanmagan.")
        return "\n".join(lines)

    u = db_get_user(uid) or {}
    cv_ok = bool(u.get("has_cv_access"))
    ob_ok = bool(u.get("has_objective_access"))
    flags = []
    if cv_ok:
        flags.append("CV yuklash huquqi bor")
    if ob_ok:
        flags.append("Obyektivka yuklash huquqi bor")
    if flags:
        lines.append("🎫 " + " · ".join(flags) + "\n")

    rows = _compact_doc_rows(db_list_user_paid_doc_requests(uid, limit=12))
    if not rows:
        lines.append(
            "Hali so‘rov yo‘q.\n\n"
            "📄 <b>CV Resume</b> yoki ✍️ <b>Obyektivka</b> tugmasini bosing — "
            "forma → 5 000 so‘m → admin tasdiqlash."
        )
        return "\n".join(lines)

    lines.append("<b>Oxirgi so‘rovlar:</b>")
    for r in rows:
        rid = r.get("id", "?")
        kind = str(r.get("kind") or "—").strip().lower()
        kind_uz = "CV" if kind == "cv" else "Obyektivka"
        st = paid_doc_status_label(str(r.get("status") or "pending"))
        lines.append(f"• #{rid} — {kind_uz}: {st}")

    lines.append(
        "\n💡 <b>Tasdiqlangan</b> bo‘lsa — formada «Botga yuborish».\n"
        "<b>Yuborilgan</b> bo‘lsa — yangi hujjat uchun qayta to‘lov."
    )
    return "\n".join(lines)
