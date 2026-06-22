"""Admin panel inline keyboards."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def broadcast_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="adm_bc_confirm"),
                InlineKeyboardButton(text="❌ Bekor", callback_data="adm_bc_cancel"),
            ]
        ]
    )


def export_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Users.xlsx", callback_data="adm_exp_users"),
                InlineKeyboardButton(text="Payments.xlsx", callback_data="adm_exp_payments"),
            ],
            [InlineKeyboardButton(text="Statistics.xlsx", callback_data="adm_exp_stats")],
        ]
    )


def payment_filter_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Bugungi", callback_data="adm_pay_today"),
                InlineKeyboardButton(text="Haftalik", callback_data="adm_pay_week"),
                InlineKeyboardButton(text="Oylik", callback_data="adm_pay_month"),
            ],
            [
                InlineKeyboardButton(text="Pending", callback_data="adm_pay_pending"),
                InlineKeyboardButton(text="Approved", callback_data="adm_pay_approved"),
                InlineKeyboardButton(text="Rejected", callback_data="adm_pay_rejected"),
            ],
            [InlineKeyboardButton(text="Barchasi", callback_data="adm_pay_all")],
        ]
    )


def user_profile_kb(
    telegram_id: int,
    *,
    pending_payment_id: int | None = None,
) -> InlineKeyboardMarkup:
    tid = int(telegram_id)
    rows: list[list[InlineKeyboardButton]] = []
    if pending_payment_id:
        pid = int(pending_payment_id)
        rows.append(
            [
                InlineKeyboardButton(
                    text="✅ To'lovni tasdiqlash",
                    callback_data=f"pay_approve_{pid}",
                ),
                InlineKeyboardButton(
                    text="❌ To'lovni rad etish",
                    callback_data=f"pay_reject_{pid}",
                ),
            ]
        )
    rows.extend(
        [
            [
                InlineKeyboardButton(
                    text="📄 Hujjatni ochish",
                    callback_data=f"adm_doc_open_{tid}",
                ),
                InlineKeyboardButton(
                    text="🔒 Hujjatni yopish",
                    callback_data=f"adm_doc_close_{tid}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Hujjatni tiklash",
                    callback_data=f"adm_doc_reset_{tid}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="👤 User profili",
                    callback_data=f"adm_profile_{tid}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📩 Userga xabar yuborish",
                    callback_data=f"adm_msg_{tid}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🚫 Block User",
                    callback_data=f"adm_block_{tid}",
                ),
                InlineKeyboardButton(
                    text="✅ Unblock User",
                    callback_data=f"adm_unblock_{tid}",
                ),
            ],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def document_access_kb(telegram_id: int, *, action: str) -> InlineKeyboardMarkup:
    tid = int(telegram_id)
    prefix = "adm_doc_grant" if action == "open" else "adm_doc_revoke"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📄 CV", callback_data=f"{prefix}_cv_{tid}"),
                InlineKeyboardButton(
                    text="📋 Obyektivka",
                    callback_data=f"{prefix}_oby_{tid}",
                ),
            ]
        ]
    )


def user_search_results_kb(users: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for u in users[:8]:
        tid = int(u["telegram_id"])
        label = (u.get("first_name") or str(tid))[:24]
        rows.append(
            [InlineKeyboardButton(text=label, callback_data=f"adm_user_{tid}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def support_reply_kb(telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📩 Javob berish", callback_data=f"sup_reply_{telegram_id}")]
        ]
    )


def error_filter_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Barchasi", callback_data="adm_err_all"),
                InlineKeyboardButton(text="Bot", callback_data="adm_err_bot"),
            ],
            [
                InlineKeyboardButton(text="Gemini", callback_data="adm_err_gemini"),
                InlineKeyboardButton(text="To'lov", callback_data="adm_err_payment"),
            ],
            [
                InlineKeyboardButton(text="PDF", callback_data="adm_err_pdf"),
                InlineKeyboardButton(text="DOCX", callback_data="adm_err_docx"),
            ],
        ]
    )
