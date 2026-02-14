"""
Admin Panel Handlers (Extended with Pro Features)
- Markdown escaped correctly to prevent errors.
"""
import os
import json
import logging
import asyncio
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from telegram.helpers import escape_markdown

from config import ADMIN_USER_ID, logger
from bot.services.settings_service import (
    get_channels, add_channel, remove_channel,
    get_premium_users_full, add_premium, remove_premium, is_premium,
    get_daily_limit, set_daily_limit
)
from bot.services.usage_tracker import get_today, _load_usage
import bot.services.user_service as crm

logger = logging.getLogger(__name__)

async def is_admin(user_id):
    str_id = str(user_id)
    admin_ids = str(ADMIN_USER_ID).split(',') if ADMIN_USER_ID else []
    return str_id in admin_ids

def get_admin_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📊 Statistika"), KeyboardButton("📨 Xabar yuborish")],
        [KeyboardButton("📢 Kanallar"), KeyboardButton("💎 Premium Boshqaruv")],
        [KeyboardButton("⚙️ Sozlamalar"), KeyboardButton("👥 Foydalanuvchilar")],
        [KeyboardButton("🚪 Panelni yopish")]
    ], resize_keyboard=True)

# Helper to safely format text for Markdown V2 (or basic Markdown)
def safe_md(text):
    if not text: return ""
    # Telegram Markdown legacy needs specific escaping: _ * ` [
    # But usually simpler just to replace critical ones if using basic "Markdown"
    # Or use "HTML" mode. Let's try basic manual escape for legacy Markdown mode
    return str(text).replace("_", "\\_").replace("*", "\\*").replace("`", "\\`").replace("[", "\\[")

# === COMMANDS ===

async def admin_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id): return
    await update.message.reply_text(
        "🕴 **Admin Panel (PRO v3.5)**\n\nBo'limni tanlang:",
        reply_markup=get_admin_keyboard(), parse_mode="Markdown"
    )

async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id): return
    text = update.message.text
    
    if text == "📊 Statistika":
        crm_data = crm.get_daily_crm_stats()
        await update.message.reply_text(
            f"📊 **Bot Statistikasi**\n\n"
            f"👥 Yangi Foydalanuvchilar (Bugun): **{crm_data['new_users']}** ta\n"
            f"🔥 Faol Foydalanuvchilar (Bugun): **{crm_data['active_users']}** ta\n"
            f"💎 Premium Sotilgan (Bugun): **{crm_data['premium_sales']}** ta\n\n"
            f"Batafsil: `/stats`",
            parse_mode="Markdown"
        )
        
    elif text == "📨 Xabar yuborish":
        await update.message.reply_text(
            "📨 **Xabar yuborish uchun:**\n\n"
            "1. Botga matn, rasm yoki video yuboring.\n"
            "2. O'sha xabarga **Reply** qilib `/send` deb yozing.\n"
            "3. Yoki to'g'ridan-to'g'ri yozing: `/send Assalomu alaykum!`",
            parse_mode="Markdown"
        )
        
    elif text == "📢 Kanallar":
        channels = get_channels()
        msg = "📢 **Majburiy A'zolik Kanallari:**\n\n"
        if not channels:
            msg += "⚠️ Hozircha kanallar yo'q.\n"
        else:
            for cid, cname in channels.items():
                msg += f"✅ {safe_md(cname)} (`{cid}`)\n"
        
        msg += "\n➕ **Qo'shish:** `/add_channel @username`\n➖ **O'chirish:** `/remove_channel @username`\n\n💡 Bot kanalda **Admin** bo'lishi shart!"
        await update.message.reply_text(msg, parse_mode="Markdown")
        
    elif text == "💎 Premium Boshqaruv":
        premiums = get_premium_users_full()
        active_list = []
        expired_list = []
        
        for uid, data in premiums.items():
            end_date = data.get("end_date", "N/A")
            name = safe_md(data.get("name", "Unknown"))
            info = f"👤 `{uid}` ({name}) — {end_date} gacha"
            
            if is_premium(uid):
                active_list.append("✅ " + info)
            else:
                expired_list.append("❌ " + info)
        
        msg = f"💎 **Premium Foydalanuvchilar:**\n\n"
        if active_list: msg += "**Faol:**\n" + "\n".join(active_list) + "\n\n"
        if expired_list: msg += "**Muddati tugagan:**\n" + "\n".join(expired_list) + "\n\n"
        if not active_list and not expired_list: msg += "Ro'yxat bo'sh.\n\n"
            
        msg += "➕ **Qo'shish:** `/add_premium <ID> <Kun> <Ism>`\nExample: `/add_premium 12345678 30 Ali`\n\n❌ **O'chirish:** `/remove_premium <ID>`"
        await update.message.reply_text(msg, parse_mode="Markdown")
               
    elif text == "⚙️ Sozlamalar":
        limit = get_daily_limit()
        msg = f"⚙️ **Bot Sozlamalari**\n\n📉 **Kunlik bepul limit:** {limit} ta\n\n✏️ O'zgartirish: `/set_limit 20` (0 = cheksiz)"
        await update.message.reply_text(msg, parse_mode="Markdown")
        
    elif text == "👥 Foydalanuvchilar":
        msg = (
            "👥 **Foydalanuvchilar Boshqaruvi (CRM)**\n\n"
            "• `/users` — Barcha foydalanuvchilar ro'yxati\n"
            "• `/top` — Eng faol foydalanuvchilar (Top 10)\n"
            "• `/search <ID>` — Foydalanuvchi qidirish\n"
            "• `/ban <ID>` — Bloklash\n"
            "• `/unban <ID>` — Blokni ochish\n\n"
            "Misol: `/search 12345678`"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    elif text == "🚪 Panelni yopish":
        from bot.keyboards.reply_keyboards import get_main_menu
        await update.message.reply_text("🏠 Bosh menyuga qaytildi.", reply_markup=get_main_menu())

# === PAGINATION HELPER (With Escaping) ===

async def show_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE, page=1):
    profiles = crm.get_all_profiles()
    if not profiles:
        await update.message.reply_text("📂 Baza bo'sh.")
        return

    sorted_profiles = sorted(
        profiles.values(), 
        key=lambda x: x.get("joined_at", ""), 
        reverse=True
    )
    
    per_page = 15
    total = len(sorted_profiles)
    start = (page - 1) * per_page
    end = start + per_page
    
    page_items = sorted_profiles[start:end]
    
    if not page_items:
        await update.message.reply_text("⚠️ Boshqa sahifa yo'q.")
        return

    msg = f"👥 **Foydalanuvchilar Ro'yxati ({start+1}-{min(end, total)} / {total})**\n\n"
    
    for p in page_items:
        uid = p.get('id', 'N/A')
        name = safe_md(p.get('first_name', 'Unknown'))
        username = safe_md(p.get('username'))
        
        # User Link Logic
        if username and username != "None":
            user_link = f"@{username}"
        else:
            user_link = f"[{name}](tg://user?id={uid})"
        
        joined = p.get('joined_at', '').split(' ')[0]
        files = p.get('files_processed', 0)
        sessions = p.get('sessions', 0)
        
        status_icon = "🟢"
        if p.get('is_banned', False): status_icon = "🔴"
        elif is_premium(uid): status_icon = "💎"
        
        msg += (
            f"{status_icon} {user_link} (`{uid}`)\n"
            f"   📅 {joined} | 📄 {files} | 🔄 {sessions}\n"
        )
    
    msg += f"\n💡 Sahifa: `/users {page+1}`"
    
    try:
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error sending users list: {e}")
        await update.message.reply_text("⚠️ Ro'yxatni chiqarishda xatolik (belgilar muammosi). Ismlarda maxsus belgilar bo'lishi mumkin.")


# === COMMANDS ===

async def user_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id): return
    
    if not context.args:
        await show_users_list(update, context, page=1)
        return
    
    arg = context.args[0]
    if arg.isdigit() and len(arg) < 4:
        await show_users_list(update, context, page=int(arg))
        return

    uid = arg
    profile = crm.get_user_profile(uid)
    
    if not profile:
        await update.message.reply_text("❌ Foydalanuvchi topilmadi.")
        return
        
    prem_hist = profile.get("premium_history", [])
    prem_msg = "Yo'q"
    if prem_hist:
        prem_msg = "\n"
        for h in prem_hist:
            prem_msg += f"  - {h.get('date', 'N/A')}: {h.get('days')} kun (by {safe_md(h.get('given_by', 'Admin'))})\n"
            
    files = profile.get('files_processed', 0)
    sessions = profile.get('sessions', 0)
    last_srv = safe_md(profile.get('last_service', 'None'))
    is_banned = profile.get('is_banned', False)
    
    name = safe_md(profile.get('first_name', 'Unknown'))
    username = safe_md(profile.get('username'))
    
    if username and username != "None":
        link_md = f"@{username}"
    else:
        link_md = f"[{name}](tg://user?id={uid})"
            
    msg = (
        f"👤 **Foydalanuvchi Profili**\n\n"
        f"🆔 ID: `{uid}`\n"
        f"🏷 Ism: {link_md}\n"
        f"📅 Joined: {profile.get('joined_at')}\n"
        f"🕒 Last Active: {profile.get('last_active')}\n"
        f"🚫 Status: {'**BANNED** 🔴' if is_banned else 'ACTIVE 🟢'}\n\n"
        f"📊 **Statistika:**\n"
        f"📄 Fayllar: **{files}** ta\n"
        f"🔄 Sessiyalar: **{sessions}** ta\n"
        f"🛠 Oxirgi xizmat: **{last_srv}**\n\n"
        f"💎 **Premium Tarixi:** {prem_msg}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await user_info_command(update, context)

async def top_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id): return
    
    profiles = crm.get_all_profiles()
    if not profiles:
        await update.message.reply_text("📂 Baza bo'sh.")
        return
        
    sorted_profiles = sorted(
        profiles.values(), 
        key=lambda x: x.get("files_processed", 0), 
        reverse=True
    )[:10]
    
    msg = "🏆 **Top 10 Faol Foydalanuvchilar (Fayllar bo'yicha)**\n\n"
    
    for i, p in enumerate(sorted_profiles, 1):
        uid = p.get('id', 'N/A')
        name = safe_md(p.get('first_name', 'Unknown'))
        files = p.get('files_processed', 0)
        
        msg += f"{i}. {name} (`{uid}`) — **{files}** ta fayl\n"
        
    await update.message.reply_text(msg, parse_mode="Markdown")

async def ban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id): return
    if not context.args:
        await update.message.reply_text("⚠️ ID kiriting: `/ban 12345678`")
        return
    uid = context.args[0]
    if crm.set_ban_status(uid, True):
        await update.message.reply_text(f"🚫 Foydalanuvchi bloklandi: `{uid}`", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Foydalanuvchi topilmadi.")

async def unban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id): return
    if not context.args:
        await update.message.reply_text("⚠️ ID kiriting: `/unban 12345678`")
        return
    uid = context.args[0]
    if crm.set_ban_status(uid, False):
        await update.message.reply_text(f"✅ Foydalanuvchi blokdan chiqarildi: `{uid}`", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Foydalanuvchi topilmadi.")

async def add_premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id): return
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ `/add_premium <ID> [KUN] [ISM]`")
        return
    try:
        uid = args[0]
        days = 30
        name = "User"
        if len(args) > 1:
            try: days = int(args[1])
            except: name = " ".join(args[1:])
        if len(args) > 2: name = " ".join(args[2:])
        end_date = add_premium(uid, days, name)
        crm.log_premium_transaction(uid, days, str(update.effective_user.id))
        await update.message.reply_text(f"✅ **Premium Berildi!** 💎\nExpire: {end_date}", parse_mode="Markdown")
    except ValueError: await update.message.reply_text("❌ ID raqam bo'lishi kerak.")
    except Exception as e: await update.message.reply_text(f"❌ Xato: {e}")

async def remove_premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id): return
    if not context.args: return
    try:
        if remove_premium(context.args[0]): await update.message.reply_text(f"✅ O'chirildi: {context.args[0]}")
        else: await update.message.reply_text("❌ Topilmadi.")
    except: pass

async def set_limit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id): return
    if not context.args: return
    try:
        set_daily_limit(int(context.args[0]))
        await update.message.reply_text(f"✅ Limit: {context.args[0]}")
    except: pass

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id): return
    update.message.text = "📊 Statistika"
    await handle_admin_text(update, context)

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast"""
    if not await is_admin(update.effective_user.id): return

    msg = None
    txt = None
    if update.message.reply_to_message: msg = update.message.reply_to_message
    elif context.args: txt = " ".join(context.args)
    else: return
    
    profiles = crm.get_all_profiles()
    total = len(profiles)
    success = 0
    blocked = 0
    status_msg = await update.message.reply_text("🚀 Sending...")
    
    for uid_str in profiles.keys():
        try:
            uid = int(uid_str)
            if msg: await msg.copy(chat_id=uid)
            elif txt: await context.bot.send_message(chat_id=uid, text=txt)
            success += 1
        except TelegramError:
            blocked += 1
        await asyncio.sleep(0.05)
        
    await status_msg.edit_text(f"✅ Done: {success}/{total}. Blocked: {blocked}")

async def track_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Middleware"""
    if update.effective_user:
        if crm.is_user_banned(update.effective_user.id):
            if not await is_admin(update.effective_user.id):
                context.user_data['is_banned'] = True
                return

        cmd = None
        if update.message and update.message.text:
             if update.message.text.startswith('/start'): cmd = 'start'
             elif update.message.text.startswith('/'): cmd = 'command'
        
        crm.track_user_activity(update.effective_user, command=cmd)
