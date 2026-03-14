"""
Admin Panel Handlers (Extended with Pro Features)
- Markdown escaped correctly to prevent errors.
"""
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from config import ADMIN_USER_ID, logger
from bot.services.settings_service import (
    get_channels, add_channel, remove_channel,
    get_premium_users_full, add_premium, remove_premium, is_premium,
    get_daily_limit, set_daily_limit
)
from bot.services.support_service import (
    list_support_requests, set_support_status, support_stats, get_support_request
)
import bot.services.user_service as crm

SUPPORT_REPLY_TEMPLATES = {
    "accepted": "Qabul qilindi",
    "more_info": "Qo'shimcha ma'lumot yuboring",
    "resolved": "Yechildi",
}

async def is_admin(user_id):
    str_id = str(user_id)
    admin_ids = str(ADMIN_USER_ID).split(',') if ADMIN_USER_ID else []
    return str_id in admin_ids

def get_admin_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📊 Statistika"), KeyboardButton("📨 Xabar yuborish")],
        [KeyboardButton("📢 Kanallar"), KeyboardButton("💎 Premium Boshqaruv")],
        [KeyboardButton("⚙️ Sozlamalar"), KeyboardButton("👥 Foydalanuvchilar")],
        [KeyboardButton("🆘 Support so'rovlar")],
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

async def send_full_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send full statistics with all user details"""
    profiles = crm.get_all_profiles()
    crm_data = crm.get_daily_crm_stats()
    total = len(profiles)
    
    premiums = get_premium_users_full()
    active_prem = sum(1 for uid in premiums if is_premium(uid))
    total_files = sum(p.get('files_processed', 0) for p in profiles.values())
    banned_count = sum(1 for p in profiles.values() if p.get('is_banned', False))
    
    # Header
    header = (
        f"📊 **Bot Statistikasi**\n\n"
        f"👥 Jami obunachilar: **{total}** ta\n"
        f"🆕 Bugungi yangi: **{crm_data['new_users']}** ta\n"
        f"🔥 Bugungi faol: **{crm_data['active_users']}** ta\n"
        f"💎 Premium (faol): **{active_prem}** ta\n"
        f"📄 Jami fayllar: **{total_files}** ta\n"
        f"🚫 Bloklangan: **{banned_count}** ta\n"
        f"{'—' * 25}\n\n"
    )
    await update.message.reply_text(header, parse_mode="Markdown")
    
    if not profiles:
        return
    
    # Sort by joined_at (newest first)
    sorted_profiles = sorted(
        profiles.values(),
        key=lambda x: x.get('joined_at', ''),
        reverse=True
    )
    
    # Build user list in chunks (Telegram max 4096 chars)
    chunk = ""
    chunk_num = 1
    
    for i, p in enumerate(sorted_profiles, 1):
        uid = p.get('id', 'N/A')
        name = safe_md(p.get('first_name', 'Nomsiz'))
        username = p.get('username')
        files = p.get('files_processed', 0)
        sessions = p.get('sessions', 0)
        joined = p.get('joined_at', 'N/A')
        last_active = p.get('last_active', 'N/A')
        last_srv = safe_md(p.get('last_service', '-'))
        is_ban = p.get('is_banned', False)
        
        # Premium check
        prem_status = "💎 Ha" if is_premium(uid) else "Yo'q"
        
        # Name + Username
        uname_str = f" (@{safe_md(username)})" if username else ""
        
        # Status icon
        icon = "🔴" if is_ban else ("💎" if is_premium(uid) else "🟢")
        
        entry = (
            f"{icon} **{i}.** {name}{uname_str}\n"
            f"   🆔 `{uid}`\n"
            f"   📅 Kirdi: {joined}\n"
            f"   🕒 Faol: {last_active}\n"
            f"   💎 Premium: {prem_status}\n"
            f"   📄 Fayllar: {files} | 🔄 Kirdi: {sessions}\n"
            f"   🛠 Oxirgi: {last_srv}\n\n"
        )
        
        # Check if adding this entry exceeds limit
        if len(chunk) + len(entry) > 3800:
            await update.message.reply_text(chunk, parse_mode="Markdown")
            chunk = ""
            chunk_num += 1
        
        chunk += entry
    
    # Send remaining
    if chunk:
        await update.message.reply_text(chunk, parse_mode="Markdown")

def get_admin_cancel_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("❌ Bekor qilish")]], resize_keyboard=True)

async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id): return
    text = update.message.text
    
    if text == "📊 Statistika":
        await send_full_stats(update, context)
        
    elif text == "📨 Xabar yuborish":
        context.user_data['admin_state'] = 'broadcast'
        await update.message.reply_text(
            "📨 **Ommaviy Xabar yuborish**\n\n"
            "Yubormoqchi bo'lgan xabaringizni (matn, rasm, video) botga yuboring.\n"
            "Barcha foydalanuvchilarga xabar yetkaziladi.",
            parse_mode="Markdown",
            reply_markup=get_admin_cancel_keyboard()
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
        
        if not premiums:
            await update.message.reply_text(
                "💎 **Premium Foydalanuvchilar**\n\n"
                "⚠️ Hozircha premium foydalanuvchilar yo'q.\n\n"
                "➕ Qo'shish: `/add_premium <ID> <Kun> <Ism>`",
                parse_mode="Markdown"
            )
            return
        
        # Build inline keyboard with premium users
        buttons = []
        for uid, data in premiums.items():
            name = data.get("name", "User")
            end_date = data.get("end_date", "N/A")
            status = "✅" if is_premium(uid) else "❌"
            
            button_text = f"{status} {name} ({uid[:8]}...) — {end_date}"
            buttons.append([InlineKeyboardButton(button_text, callback_data=f"prem_view_{uid}")])
        
        # Add "Add New" button
        buttons.append([InlineKeyboardButton("➕ Yangi Premium Qo'shish", callback_data="prem_add_new")])
        
        keyboard = InlineKeyboardMarkup(buttons)
        
        await update.message.reply_text(
            "💎 **Premium Foydalanuvchilar**\n\n"
            "Boshqarish uchun foydalanuvchini tanlang:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
               
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

    elif text == "🆘 Support so'rovlar":
        await show_support_requests_panel(update, context)

    elif text == "🚪 Panelni yopish":
        from bot.keyboards.reply_keyboards import get_main_menu
        await update.message.reply_text("🏠 Bosh menyuga qaytildi.", reply_markup=get_main_menu(update.effective_user.id if update.effective_user else None))

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
        username = p.get('username')
        
        uname_str = f" (@{safe_md(username)})" if username else ""
        
        joined = p.get('joined_at', '').split(' ')[0]
        files = p.get('files_processed', 0)
        sessions = p.get('sessions', 0)
        
        status_icon = "🟢"
        if p.get('is_banned', False): status_icon = "🔴"
        elif is_premium(uid): status_icon = "💎"
        
        msg += (
            f"{status_icon} {name}{uname_str} (`{uid}`)\n"
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
    username = profile.get('username')
    
    uname_line = f"📱 Username: @{safe_md(username)}\n" if username else ""
            
    msg = (
        f"👤 **Foydalanuvchi Profili**\n\n"
        f"🏷 Ism: {name}\n"
        f"{uname_line}"
        f"🆔 ID: `{uid}`\n"
        f"📅 Qo'shilgan: {profile.get('joined_at')}\n"
        f"🕒 Oxirgi faol: {profile.get('last_active')}\n"
        f"🚫 Status: {'**BANNED** 🔴' if is_banned else 'ACTIVE 🟢'}\n\n"
        f"📊 **Statistika:**\n"
        f"📄 Fayllar: **{files}** ta\n"
        f"🔄 Kirdi: **{sessions}** marta\n"
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
        username = p.get('username')
        files = p.get('files_processed', 0)
        
        uname_str = f" (@{safe_md(username)})" if username else ""
        msg += f"{i}. {name}{uname_str} (`{uid}`) — **{files}** ta fayl\n"
        
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
    await send_full_stats(update, context)

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
async def add_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("⚠️ Foydalanish: /add_channel @username")
        return

    username = context.args[0]

    try:
        add_channel(username, username)
        await update.message.reply_text(f"✅ Kanal qo'shildi: {username}")
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {e}")
async def remove_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("⚠️ Foydalanish: /remove_channel @username")
        return

    username = context.args[0]
    if remove_channel(username):
        await update.message.reply_text(f"✅ O'chirildi: {username}")
    else:
        await update.message.reply_text("❌ Kanal topilmadi.")

async def process_admin_state_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id): return
    
    state = context.user_data.get('admin_state')
    if not state: return False # Returns False so main.py can pass it to other handlers if not handled
    
    text = update.message.text if update.message else ""
    
    if text == "❌ Bekor qilish":
        context.user_data.pop('admin_state', None)
        context.user_data.pop('support_reply_user_id', None)
        context.user_data.pop('support_reply_req_id', None)
        await update.message.reply_text("🚫 Bekor qilindi.", reply_markup=get_admin_keyboard())
        return True
        
    if state == 'broadcast':
        msg = update.message
        profiles = crm.get_all_profiles()
        success = 0
        blocked = 0
        
        status_msg = await update.message.reply_text("🚀 Ommaviy xabar yuborilmoqda...")
        
        for uid_str in profiles.keys():
            try:
                uid = int(uid_str)
                await msg.copy(chat_id=uid)
                success += 1
            except TelegramError:
                blocked += 1
            await asyncio.sleep(0.05)
            
        try:
            await status_msg.delete()
        except Exception:
            pass
            
        await update.message.reply_text(
            f"✅ Tugatildi:\n\nYetib bordi: {success} ta\nYetib bormadi (Bloklangan): {blocked} ta",
            reply_markup=get_admin_keyboard()
        )
        context.user_data.pop('admin_state', None)
        return True
        
    elif state == 'add_premium':
        if not text:
            await update.message.reply_text("❓ Iltimos, ma'lumotlarni matn ko'rinishida yuboring.")
            return True
        
        parts = text.split(maxsplit=2)
        if len(parts) < 1:
            return True
            
        try:
            uid = parts[0]
            days = 30
            name = "User"
            if len(parts) > 1:
                try: days = int(parts[1])
                except Exception: name = " ".join(parts[1:])
            if len(parts) > 2: name = parts[2]
            
            end_date = add_premium(uid, days, name)
            crm.log_premium_transaction(uid, days, str(update.effective_user.id))
            await update.message.reply_text(f"✅ **Premium Berildi!** 💎\nExpire: {end_date}", parse_mode="Markdown", reply_markup=get_admin_keyboard())
            context.user_data.pop('admin_state', None)
        except Exception as e:
            await update.message.reply_text(f"❌ Xato: {e}")
        return True
    
    elif state == 'add_channel':
        if not text or not text.startswith('@'):
            await update.message.reply_text("❓ Iltimos, kanal username'ini @ belgi bilan boshlang (masalan: @dasturchi).")
            return True
        try:
            add_channel(text, text)
            await update.message.reply_text(f"✅ Kanal qo'shildi: {text}", reply_markup=get_admin_keyboard())
            context.user_data.pop('admin_state', None)
        except Exception as e:
            await update.message.reply_text(f"❌ Xato: {e}")
        return True

    elif state == 'support_reply':
        target_uid = context.user_data.get('support_reply_user_id')
        req_id = context.user_data.get('support_reply_req_id')
        reply_text = (text or "").strip()
        if not target_uid:
            await update.message.reply_text("❌ Target user topilmadi.", reply_markup=get_admin_keyboard())
            context.user_data.pop('admin_state', None)
            return True
        if not reply_text:
            await update.message.reply_text("❓ Javob matnini yuboring yoki bekor qiling.")
            return True
        try:
            await context.bot.send_message(
                chat_id=int(target_uid),
                text=f"📩 Admin javobi:\n\n{reply_text}",
            )
            if req_id:
                set_support_status(int(req_id), "resolved")
            await update.message.reply_text(
                f"✅ Javob foydalanuvchiga yuborildi (ID: <code>{target_uid}</code>).",
                parse_mode="HTML",
                reply_markup=get_admin_keyboard()
            )
        except Exception as e:
            await update.message.reply_text(
                f"❌ Yuborishda xatolik: {e}",
                reply_markup=get_admin_keyboard()
            )
        finally:
            context.user_data.pop('admin_state', None)
            context.user_data.pop('support_reply_user_id', None)
            context.user_data.pop('support_reply_req_id', None)
        return True

    return False


async def _send_support_reply_to_user(
    context: ContextTypes.DEFAULT_TYPE,
    target_uid: int,
    reply_text: str,
    req_id: int | None = None,
):
    await context.bot.send_message(
        chat_id=int(target_uid),
        text=f"📩 Admin javobi:\n\n{reply_text}",
    )
    if req_id:
        set_support_status(int(req_id), "resolved")


def _build_support_panel_payload():
    stats = support_stats()
    items = list_support_requests(status="open", limit=10)
    header = (
        "🆘 <b>Support so'rovlar paneli</b>\n\n"
        f"📥 Ochiq: <b>{stats['open']}</b>\n"
        f"✅ Yopilgan: <b>{stats['resolved']}</b>\n"
        f"📚 Jami: <b>{stats['total']}</b>\n\n"
    )
    if not items:
        return header + "Hozircha ochiq so'rovlar yo'q.", None

    lines = []
    keyboard_rows = []
    for req in items:
        rid = req.get("id")
        uid = req.get("user_id")
        uname = req.get("username") or "yo'q"
        source = req.get("source") or "unknown"
        created = req.get("created_at") or "-"
        msg = (req.get("message") or "").strip().replace("\n", " ")
        if len(msg) > 120:
            msg = msg[:117] + "..."
        lines.append(
            f"🎫 <b>#{rid}</b> | {created}\n"
            f"🆔 <code>{uid}</code> | 👤 @{uname}\n"
            f"🌐 Manba: <b>{source}</b>\n"
            f"💬 {msg}\n"
        )
        keyboard_rows.append([
            InlineKeyboardButton(f"✉️ Javob #{rid}", callback_data=f"support_reply_{rid}"),
            InlineKeyboardButton(f"✅ Yopish #{rid}", callback_data=f"support_resolve_{rid}")
        ])

    keyboard_rows.append([InlineKeyboardButton("🔄 Yangilash", callback_data="support_refresh")])
    kb = InlineKeyboardMarkup(keyboard_rows) if keyboard_rows else None
    return header + "\n".join(lines), kb


async def show_support_requests_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return
    text, kb = _build_support_panel_payload()
    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=kb
    )


async def support_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    if not await is_admin(query.from_user.id):
        await query.answer("Ruxsat yo'q", show_alert=True)
        return

    data = query.data or ""
    if data == "support_refresh":
        await query.answer("Yangilandi")
        text, kb = _build_support_panel_payload()
        await query.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
        return

    if data.startswith("support_reply_"):
        req_id = data.replace("support_reply_", "", 1)
        if not req_id.isdigit():
            await query.answer("Noto'g'ri ID", show_alert=True)
            return
        req = get_support_request(int(req_id))
        if not req:
            await query.answer("So'rov topilmadi", show_alert=True)
            return
        target_uid = req.get("user_id")
        if not target_uid:
            await query.answer("Foydalanuvchi ID topilmadi", show_alert=True)
            return

        template_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Qabul qilindi", callback_data=f"support_tpl_accepted_{req_id}")],
            [InlineKeyboardButton("Qo'shimcha ma'lumot yuboring", callback_data=f"support_tpl_more_info_{req_id}")],
            [InlineKeyboardButton("Yechildi", callback_data=f"support_tpl_resolved_{req_id}")],
            [InlineKeyboardButton("✍️ Qo'lda yozish", callback_data=f"support_manual_{req_id}")],
        ])
        await query.answer("Javob turini tanlang", show_alert=False)
        await query.message.reply_text(
            "✍️ <b>Support javobi</b>\n\n"
            f"🎫 So'rov: <b>#{req_id}</b>\n"
            f"🆔 User ID: <code>{target_uid}</code>\n\n"
            "Quyidagidan birini tanlang yoki qo'lda javob yozing.",
            parse_mode="HTML",
            reply_markup=template_kb
        )
        return

    if data.startswith("support_manual_"):
        req_id = data.replace("support_manual_", "", 1)
        if not req_id.isdigit():
            await query.answer("Noto'g'ri ID", show_alert=True)
            return
        req = get_support_request(int(req_id))
        if not req:
            await query.answer("So'rov topilmadi", show_alert=True)
            return
        target_uid = req.get("user_id")
        if not target_uid:
            await query.answer("Foydalanuvchi ID topilmadi", show_alert=True)
            return
        context.user_data['admin_state'] = 'support_reply'
        context.user_data['support_reply_user_id'] = int(target_uid)
        context.user_data['support_reply_req_id'] = int(req_id)
        await query.answer("Qo'lda javob rejimi yoqildi", show_alert=False)
        await query.message.reply_text(
            "✍️ <b>Support javob rejimi</b>\n\n"
            f"🎫 So'rov: <b>#{req_id}</b>\n"
            f"🆔 User ID: <code>{target_uid}</code>\n\n"
            "Foydalanuvchiga yuboriladigan javobni matn sifatida yuboring.",
            parse_mode="HTML",
            reply_markup=get_admin_cancel_keyboard()
        )
        return

    if data.startswith("support_tpl_"):
        parts = data.split("_")
        if len(parts) < 4:
            await query.answer("Noto'g'ri template callback", show_alert=True)
            return
        template_key = "_".join(parts[2:-1])
        req_id = parts[-1]
        if not req_id.isdigit():
            await query.answer("Noto'g'ri request ID", show_alert=True)
            return
        req = get_support_request(int(req_id))
        if not req:
            await query.answer("So'rov topilmadi", show_alert=True)
            return
        target_uid = req.get("user_id")
        if not target_uid:
            await query.answer("Foydalanuvchi ID topilmadi", show_alert=True)
            return
        template_text = SUPPORT_REPLY_TEMPLATES.get(template_key)
        if not template_text:
            await query.answer("Template topilmadi", show_alert=True)
            return
        try:
            await _send_support_reply_to_user(
                context,
                int(target_uid),
                template_text,
                int(req_id),
            )
            await query.answer("Template yuborildi", show_alert=False)
            await query.message.reply_text(
                f"✅ Template javob yuborildi (#{req_id}, ID: <code>{target_uid}</code>).",
                parse_mode="HTML"
            )
        except Exception as e:
            await query.answer("Yuborishda xatolik", show_alert=False)
            await query.message.reply_text(f"❌ Xato: {e}")
        return

    if data.startswith("support_resolve_"):
        req_id = data.replace("support_resolve_", "", 1)
        ok = False
        if req_id.isdigit():
            ok = set_support_status(int(req_id), "resolved")
        await query.answer("Yopildi" if ok else "Topilmadi", show_alert=False)
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await query.message.reply_text(
            f"✅ So'rov #{req_id} yopildi." if ok else "❌ So'rov topilmadi.",
            parse_mode="HTML"
        )
