"""
Premium Management Callback Handler
Handles inline button clicks for premium user management.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.services.settings_service import (
    get_premium_users_full, add_premium, remove_premium, is_premium
)
import bot.services.user_service as crm
from bot.handlers.admin import is_admin

async def premium_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle premium management inline button callbacks"""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        await query.answer("⛔ Sizda ruxsat yo'q.", show_alert=True)
        return
    
    data = query.data
    
    # View premium user details
    if data.startswith("prem_view_"):
        uid = data.replace("prem_view_", "")
        premiums = get_premium_users_full()
        
        if uid not in premiums:
            await query.edit_message_text("❌ Foydalanuvchi topilmadi.")
            return
        
        user_data = premiums[uid]
        profile = crm.get_user_profile(uid)
        
        # Get real name and username from CRM profile
        if profile:
            real_name = profile.get("first_name", "User")
            username = profile.get("username")
            files = profile.get("files_processed", 0)
            joined = profile.get("joined_at", "N/A")
        else:
            real_name = user_data.get("name", "User")
            username = None
            files = 0
            joined = "N/A"
        
        end_date = user_data.get("end_date", "N/A")
        is_active = is_premium(uid)
        
        status_text = "✅ **Faol**" if is_active else "❌ **Muddati tugagan**"
        
        # Build message with all details
        username_line = f"📱 Username: @{username}\n" if username else ""
        
        msg = (
            f"💎 **Premium Foydalanuvchi**\n\n"
            f"👤 Ism: {real_name}\n"
            f"{username_line}"
            f"🆔 ID: `{uid}`\n"
            f"📅 Qo'shilgan: {joined}\n"
            f"⏳ Tugash sanasi: **{end_date}**\n"
            f"📊 Status: {status_text}\n"
            f"📄 Fayllar: {files} ta\n\n"
            f"Boshqarish uchun tugmani tanlang:"
        )
        
        # Management buttons
        buttons = [
            [InlineKeyboardButton("➕ 30 Kun Uzaytirish", callback_data=f"prem_extend_{uid}")],
            [InlineKeyboardButton("♾️ Umrlik Premium", callback_data=f"prem_lifetime_{uid}")],
            [InlineKeyboardButton("❌ Premium Olib Tashlash", callback_data=f"prem_remove_{uid}")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="prem_back")]
        ]
        
        keyboard = InlineKeyboardMarkup(buttons)
        await query.edit_message_text(msg, reply_markup=keyboard, parse_mode="Markdown")
    
    # Extend premium by 30 days
    elif data.startswith("prem_extend_"):
        uid = data.replace("prem_extend_", "")
        try:
            end_date = add_premium(uid, days=30)
            crm.log_premium_transaction(uid, 30, str(query.from_user.id))
            await query.answer("✅ Premium 30 kunga uzaytirildi!", show_alert=True)
            
            # Refresh view
            await query.edit_message_text(
                f"✅ Premium 30 kunga uzaytirildi!\n\n"
                f"Yangi tugash sanasi: **{end_date}**",
                parse_mode="Markdown"
            )
        except Exception as e:
            await query.answer(f"❌ Xato: {e}", show_alert=True)
    
    # Set lifetime premium
    elif data.startswith("prem_lifetime_"):
        uid = data.replace("prem_lifetime_", "")
        try:
            # Set to 100 years from now (effectively lifetime)
            end_date = add_premium(uid, days=36500)  # 100 years
            crm.log_premium_transaction(uid, 36500, str(query.from_user.id))
            await query.answer("✅ Umrlik premium berildi!", show_alert=True)
            
            await query.edit_message_text(
                f"✅ **Umrlik Premium Berildi!** ♾️\n\n"
                f"Tugash sanasi: **{end_date}** (100 yil)",
                parse_mode="Markdown"
            )
        except Exception as e:
            await query.answer(f"❌ Xato: {e}", show_alert=True)
    
    # Remove premium
    elif data.startswith("prem_remove_"):
        uid = data.replace("prem_remove_", "")
        try:
            if remove_premium(uid):
                await query.answer("✅ Premium olib tashlandi!", show_alert=True)
                await query.edit_message_text(
                    f"✅ Premium olib tashlandi.\n\n"
                    f"User ID: `{uid}`",
                    parse_mode="Markdown"
                )
            else:
                await query.answer("❌ Foydalanuvchi topilmadi.", show_alert=True)
        except Exception as e:
            await query.answer(f"❌ Xato: {e}", show_alert=True)
    
    # Back to premium list
    elif data == "prem_back":
        premiums = get_premium_users_full()
        
        if not premiums:
            await query.edit_message_text(
                "💎 **Premium Foydalanuvchilar**\n\n"
                "⚠️ Hozircha premium foydalanuvchilar yo'q.",
                parse_mode="Markdown"
            )
            return
        
        buttons = []
        for uid, user_data in premiums.items():
            name = user_data.get("name", "User")
            end_date = user_data.get("end_date", "N/A")
            status = "✅" if is_premium(uid) else "❌"
            
            button_text = f"{status} {name} ({uid[:8]}...) — {end_date}"
            buttons.append([InlineKeyboardButton(button_text, callback_data=f"prem_view_{uid}")])
        
        buttons.append([InlineKeyboardButton("➕ Yangi Premium Qo'shish", callback_data="prem_add_new")])
        
        keyboard = InlineKeyboardMarkup(buttons)
        
        await query.edit_message_text(
            "💎 **Premium Foydalanuvchilar**\n\n"
            "Boshqarish uchun foydalanuvchini tanlang:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    # Add new premium (show instructions)
    elif data == "prem_add_new":
        from bot.handlers.admin import get_admin_cancel_keyboard
        context.user_data['admin_state'] = 'add_premium'
        
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=(
                "➕ **Yangi Premium Qo'shish**\n\n"
                "Iltimos, foydalanuvchining ma'lumotlarini bo'sh joy qoldirib yozing.\n"
                "Tartib: `ID Raqam` `Kun (misol: 30)` `To'liq ism (ixtiyoriy)`\n\n"
                "Misol: `123456789 30 Ali Valiyev`"
            ),
            parse_mode="Markdown",
            reply_markup=get_admin_cancel_keyboard()
        )
        await query.message.delete()
