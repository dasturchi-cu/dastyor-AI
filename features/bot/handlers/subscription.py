"""Subscription callback handler — 'I subscribed' check button."""
from __future__ import annotations

from aiogram import Router
from aiogram.types import CallbackQuery

from shared.subscription import (
    build_subscribe_keyboard,
    build_subscribe_text,
    get_unsubscribed_channels,
)

router = Router()


@router.callback_query(lambda c: c.data == "sub_check")
async def sub_check_callback(callback: CallbackQuery) -> None:
    """Re-check subscription status when user clicks 'I subscribed'."""
    user_id = callback.from_user.id if callback.from_user else 0
    if not user_id:
        await callback.answer("Xatolik yuz berdi.", show_alert=True)
        return

    bot = callback.bot
    if bot is None:
        await callback.answer("Xatolik yuz berdi.", show_alert=True)
        return

    unsubscribed = await get_unsubscribed_channels(bot, user_id)

    if not unsubscribed:
        # All channels subscribed!
        await callback.answer("✅ Rahmat! Obuna tasdiqlandi.", show_alert=True)
        if callback.message:
            from shared.keyboards import main_menu_keyboard
            from shared.marketing import welcome_message

            try:
                await callback.message.answer(
                    welcome_message(),
                    reply_markup=main_menu_keyboard(user_id),
                )
                try:
                    await callback.message.delete()
                except Exception:
                    pass
            except Exception:
                try:
                    await callback.message.edit_text(
                        "✅ Obuna tasdiqlandi! Botdan foydalanishingiz mumkin."
                    )
                except Exception:
                    pass
    else:
        # Still not subscribed
        await callback.answer(
            "❌ Hali barcha kanallarga obuna bo'lmadingiz!", show_alert=True
        )
        text = build_subscribe_text(unsubscribed)
        keyboard = build_subscribe_keyboard(unsubscribed)
        if callback.message:
            try:
                await callback.message.edit_text(text, reply_markup=keyboard)
            except Exception:
                pass
