"""Admin panel — Majburiy kanallar (required channels) boshqaruvi."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.repositories import required_channels as channels_repo
from features.admin.dispatch import is_admin
from features.admin.keyboards import channel_delete_confirm_kb, channels_list_kb
from features.admin.states import AdminStates
from shared.async_db import run as db_run

logger = logging.getLogger(__name__)
router = Router()


def _channels_text(channels: list[dict]) -> str:
    active = [ch for ch in channels if ch.get("is_active")]
    if not active:
        return (
            "📢 <b>Majburiy kanallar</b>\n\n"
            "Hozircha hech qanday kanal qo'shilmagan.\n"
            "Kanal qo'shish uchun <b>➕ Kanal qo'shish</b> tugmasini bosing."
        )
    lines = ["📢 <b>Majburiy kanallar ro'yxati:</b>\n"]
    for i, ch in enumerate(active, 1):
        title = ch.get("title") or ch["channel_id"]
        cid = ch["channel_id"]
        lines.append(f"{i}. <b>{title}</b> — <code>{cid}</code>")
    lines.append(
        f"\n<i>Jami: {len(active)} ta faol kanal</i>\n\n"
        "Foydalanuvchilar botdan foydalanish uchun "
        "bu kanallarga obuna bo'lishlari shart."
    )
    return "\n".join(lines)


# ── Show channels list ───────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_ch_list")
async def show_channels_list(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q.", show_alert=True)
        return
    await state.clear()
    channels = await db_run(channels_repo.get_all_channels)
    text = _channels_text(channels)
    kb = channels_list_kb(channels)
    if callback.message:
        try:
            await callback.message.edit_text(text, reply_markup=kb)
        except Exception:
            await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


# ── Add channel — ask for username ───────────────────────────────────────────

@router.callback_query(F.data == "adm_ch_add")
async def add_channel_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q.", show_alert=True)
        return
    await state.set_state(AdminStates.add_channel)
    if callback.message:
        await callback.message.answer(
            "📢 <b>Kanal qo'shish</b>\n\n"
            "Kanalning <b>username</b> ini yuboring:\n"
            "<code>@kanalUsername</code>\n\n"
            "Yoki kanalning <b>ID</b> sini yuboring:\n"
            "<code>-1001234567890</code>\n\n"
            "❗ Bot kanalning <b>adminstratori</b> bo'lishi shart!\n\n"
            "Bekor qilish uchun /cancel yozing."
        )
    await callback.answer()


@router.message(AdminStates.add_channel, F.text)
async def add_channel_receive(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return

    text = (message.text or "").strip()
    if text.lower() == "/cancel":
        await state.clear()
        await message.answer("❌ Bekor qilindi.")
        return

    # Normalize channel_id
    channel_id = text
    if not channel_id.startswith("@") and not channel_id.lstrip("-").isdigit():
        # Try adding @ prefix
        channel_id = f"@{channel_id}"

    # Try to get channel info via bot
    bot = message.bot
    title = channel_id
    invite_link = ""

    try:
        chat = await bot.get_chat(channel_id)
        title = chat.title or channel_id
        # Get invite link if possible
        try:
            invite_link = (
                getattr(chat, "invite_link", None)
                or getattr(chat, "username", None)
                and f"https://t.me/{chat.username}"
                or ""
            )
        except Exception:
            pass
        # Use the canonical ID (numeric) for consistency
        if chat.id:
            channel_id = str(chat.id)
    except Exception as exc:
        await message.answer(
            f"❌ <b>Kanal topilmadi!</b>\n\n"
            f"Xatolik: <code>{exc}</code>\n\n"
            "Iltimos, botni kanalga <b>admin</b> sifatida qo'shing va qaytadan urinib ko'ring."
        )
        return

    # Save to DB
    await db_run(
        channels_repo.add_channel,
        channel_id,
        title=title,
        invite_link=invite_link or "",
        added_by=message.from_user.id,
    )

    await state.clear()
    await message.answer(
        f"✅ <b>Kanal muvaffaqiyatli qo'shildi!</b>\n\n"
        f"📢 Kanal: <b>{title}</b>\n"
        f"🆔 ID: <code>{channel_id}</code>\n\n"
        f"Endi foydalanuvchilar bu kanalga obuna bo'lmay turib botdan foydalana olmaydi."
    )

    # Refresh list
    channels = await db_run(channels_repo.get_all_channels)
    kb = channels_list_kb(channels)
    await message.answer(_channels_text(channels), reply_markup=kb)


# ── Delete channel ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_ch_del_"))
async def delete_channel_confirm(callback: CallbackQuery) -> None:
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q.", show_alert=True)
        return

    data = callback.data or ""
    # adm_ch_del_confirm_<id> OR adm_ch_del_<id>
    if "confirm" in data:
        row_id = int(data.split("_")[-1])
        await db_run(channels_repo.remove_channel_by_id, row_id)
        await callback.answer("✅ Kanal o'chirildi!", show_alert=True)
        channels = await db_run(channels_repo.get_all_channels)
        kb = channels_list_kb(channels)
        if callback.message:
            try:
                await callback.message.edit_text(_channels_text(channels), reply_markup=kb)
            except Exception:
                await callback.message.answer(_channels_text(channels), reply_markup=kb)
    else:
        row_id = int(data.replace("adm_ch_del_", ""))
        if callback.message:
            try:
                await callback.message.edit_reply_markup(
                    reply_markup=channel_delete_confirm_kb(row_id)
                )
            except Exception:
                pass
        await callback.answer()


# ── Channel info ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_ch_info_"))
async def channel_info(callback: CallbackQuery) -> None:
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q.", show_alert=True)
        return
    await callback.answer(
        "Kanal ma'lumotlarini ko'rish uchun ro'yxatdan foydalaning.", show_alert=False
    )
