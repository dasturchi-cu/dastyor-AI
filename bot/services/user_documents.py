"""Foydalanuvchi hujjatlari — paid_doc_requests ko‘rinishi."""
from __future__ import annotations

from bot.services.bot_notify import paid_doc_status_label
from bot.services.supabase_db import (
    db_get_user,
    db_list_user_paid_doc_requests,
    has_db,
)


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

    rows = db_list_user_paid_doc_requests(uid, limit=6)
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
