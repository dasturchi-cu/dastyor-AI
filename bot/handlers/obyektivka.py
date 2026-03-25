from telegram import Update, InputFile, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
from bot.keyboards.reply_keyboards import get_back_button
import os
import time
import logging
import asyncio
from bot.utils.progress import send_progress, update_progress
from bot.services.ai_service import (
    transcribe_audio,
    extract_obyektivka_data,
    is_valid_transcription_text,
)
from config import WEBAPP_BASE, WEBAPP_VERSION
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

async def process_obyektivka_from_audio_path(context, audio_path, chat_id, user_id):
    """
    Core logic: Transcribe -> Extract Data -> WebApp link (prefill).
    Kvota bu yerda yemaydi — foydalanuvchi avval formani ko‘rib, Word/PDF yuklashda
    /api va sendData orqali limit tekshiriladi.
    """
    # Initial Progress
    progress_msg = await send_progress(context, chat_id, "Audio tahlil qilinmoqda...")
    try:
        await update_progress(context, progress_msg, 20, "Matn o'qilmoqda (Whisper)...")
        
        # 1. Transcribe
        transcribed_text = await transcribe_audio(audio_path)
        
        if not is_valid_transcription_text(transcribed_text):
            await progress_msg.edit_text(
                "❌ Audio tushunarsiz yoki STT xatosi. Iltimos, qisqa ovozli xabar yuboring (o'zbek tilida, aniq gapiring)."
            )
            return

        await update_progress(context, progress_msg, 50, "Ma'lumotlar ajratilmoqda (AI)...")
        
        # 2. Extract Data
        extracted_data = await extract_obyektivka_data(transcribed_text)
        
        if not extracted_data:
            await progress_msg.edit_text("❌ Ma'lumotlarni ajratib bo'lmadi. To'liqroq gapirib bering.")
            return
            
        await update_progress(context, progress_msg, 80, "Web-shaklga bog'lanmoqda...")

        # 3. Save data — persistent (user_profiles) + temp file fallback
        from bot.services.user_service import save_pending_oby_data
        save_pending_oby_data(user_id, extracted_data)

        os.makedirs("temp", exist_ok=True)
        json_path = f"temp/oby_data_{user_id}.json"
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(extracted_data, f, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving temp json: {e}")
        
        await update_progress(context, progress_msg, 100, "Tayyor!")

        try:
            from bot.services.supabase_db import db_insert_action_log

            tr = (transcribed_text or "").strip()
            db_insert_action_log(
                int(user_id),
                "obyektivka_voice",
                None,
                {
                    "fullname": (extracted_data.get("fullname") or "")[:120],
                    "transcript_preview": tr[:2000],
                    "transcript_chars": len(tr),
                },
            )
        except Exception:
            pass

        # 4. Give webapp link (form opens with autoload=1 → fields prefilled from API)
        kb = [[InlineKeyboardButton(
            "📋 Obyektivkani ochish",
            web_app=WebAppInfo(url=f"{WEBAPP_BASE}/obyektivka.html?autoload=1&telegram_id={user_id}&v={WEBAPP_VERSION}")
        )]]

        fn = extracted_data.get("fullname") or ""
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                (f"👤 {fn}\n\n" if fn else "")
                + "✅ Obyektivka to'ldirildi — formada ma'lumotlarni tekshirib, Word/PDF yuklab oling.\n\n"
                + "💡 Word/PDF faylni botga yuborish tarif bo‘yicha; formani avval bepul ko‘rib chiqishingiz mumkin."
            ),
            reply_markup=InlineKeyboardMarkup(kb),
        )
        await progress_msg.delete()
        
    except Exception as e:
        logger.error(f"Obyektivka Process Error: {e}", exc_info=True)
        await progress_msg.edit_text(f"❌ Xatolik: {e}")


async def obyektivka_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle Obyektivka AI module entry point.
    """
    instruction_text = (
        "📌 **Obyektivka tayyorlash uchun quyidagi ma'lumotlarni audiodagi kabi o'qib jo'nating:**\n\n"
        "1\\. F\\.I\\.Sh\\. \\(Familiyasi, ismi, sharifi\\)\n"
        "2\\. Tug'ilgan yili, oyi, sanasi\n"
        "3\\. Tug'ilgan joyi \\(viloyat, tuman/shahar\\)\n"
        "4\\. Millati\n"
        "5\\. Ma'lumoti\n"
        "6\\. Tamomlagan o'quv yurti \\(nomi va yili\\)\n"
        "7\\. Mutaxassisligi \\(diplom bo'yicha\\)\n"
        "8\\. Partiyaviyligi\n"
        "9\\. Ilmiy darajasi\n"
        "10\\. Ilmiy unvoni\n"
        "11\\. Qaysi chet tillarini biladi\n"
        "12\\. Davlat mukofotlari bilan taqdirlanganligi\n"
        "13\\. Deputatlar kengashi a'zoligi \\(ha/yo'q, qaysi kengash\\)\n"
        "14\\. Mehnat faoliyati \\(qayerda, qaysi lavozimda, boshlagan va tugatgan sanalari bilan\\)\n"
        "15\\. Rasm elektron variantda\n\n"
        "👨‍👩‍👧‍👦 **Oila a'zolari haqida ma'lumot:**\n"
        "_\\(Ota, ona, aka, uka, opa, singil, turmush o'rtog'i\\)_\n\n"
        "Har biri uchun quyidagilar ko'rsatiladi:\n"
        "1\\. F\\.I\\.Sh\\.\n"
        "2\\. Tug'ilgan yili va joyi\n"
        "3\\. Ish joyi va lavozimi\n"
        "4\\. Yashash manzili\n\n"
        "🎙 *Quyidagi audio namunaga o'xshab o'qib yuboring:*"
    )

    await update.message.reply_text(
        instruction_text,
        reply_markup=get_back_button(),
        parse_mode="MarkdownV2"
    )
    # Set user state ASAP (don't wait for any heavy ops)
    context.user_data['waiting_for'] = 'obyektivka_audio'

    # Send example audio in background (Telegram upload can be slow).
    async def _send_example_audio_bg(chat_id: int):
        try:
            HANDLERS_DIR = os.path.dirname(os.path.abspath(__file__))
            audio_candidates = [
                os.path.join(HANDLERS_DIR, "speech (1).mp3"),   # bot/handlers/speech (1).mp3
                os.path.join(HANDLERS_DIR, "namuna.mp3"),        # bot/handlers/namuna.mp3
                os.path.join(BASE_DIR, "namuna.mp3"),            # project root fallback
            ]
            for path in audio_candidates:
                if not path or not os.path.exists(path):
                    continue
                try:
                    # InputFile can accept a file path; avoids keeping file handles open.
                    await context.bot.send_audio(
                        chat_id=chat_id,
                        audio=InputFile(path, filename="namuna_audio.mp3"),
                        caption="🎙 *Namuna audio* — shunday qilib o'qib yuboring",
                        parse_mode="Markdown",
                    )
                    return
                except Exception as e:
                    logger.warning("Could not send example audio path=%s err=%s", path, e, exc_info=True)
                    return
            logger.warning("Example audio not found. Checked=%s", audio_candidates)
        except Exception:
            logger.debug("Example audio background send failed", exc_info=True)

    try:
        if update.effective_chat:
            asyncio.create_task(_send_example_audio_bg(update.effective_chat.id))
    except Exception:
        pass


async def handle_obyektivka_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process audio upload from menu flow"""
    message = update.message
    
    if not (message.voice or message.audio):
        await message.reply_text("❌ Iltimos, audio xabar yuboring.")
        return
    
    msg = await message.reply_text("⏳ Audio yuklanmoqda...")
    audio_path = None
    
    try:
        # Get audio file
        if message.voice:
            audio_file = await message.voice.get_file()
            ext = "ogg"
        else:
            audio_file = await message.audio.get_file()
            ext = "mp3"
        
        audio_path = f"temp_oby_{update.effective_user.id}_{int(time.time())}.{ext}"
        await audio_file.download_to_drive(audio_path)
        await msg.edit_text("⏳ Audio qabul qilindi. Qayta ishlanmoqda...")

        async def _bg(path: str):
            try:
                await process_obyektivka_from_audio_path(
                    context, path, update.effective_chat.id, update.effective_user.id
                )
            finally:
                try:
                    if path and os.path.exists(path):
                        os.remove(path)
                except Exception:
                    pass

        asyncio.create_task(_bg(audio_path))
        return
        
    except Exception as e:
        logger.error(f"Upload Error: {e}")
        await msg.edit_text(f"❌ Yuklashda xato: {e}")
        
    finally:
        # Cleanup handled in background task; if we error before task creation, remove file.
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except Exception:
                pass
        
        # Clear state handles by logic inside or caller?
        # Let's keep state unless back button pressed. BUT user might want to try again.
        # Usually we clear state only on success or back.
        # Let's leave it.


async def auto_voice_obyektivka_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Shaxsiy chatda ovoz/audio yuborilganda: menyu bosilmasdan STT → obyektivka ma'lumotlari → Web App.
    """
    message = update.message
    if not message or not update.effective_user or not update.effective_chat:
        return

    msg = await message.reply_text("⏳ Ovoz qayta ishlanmoqda...")
    audio_path = None
    try:
        if message.voice:
            audio_file = await message.voice.get_file()
            ext = "ogg"
        elif message.audio:
            audio_file = await message.audio.get_file()
            fn = (message.audio.file_name or "") or ""
            ext = fn.rsplit(".", 1)[-1][:8] if "." in fn else "mp3"
            if not ext or len(ext) > 8:
                ext = "mp3"
        else:
            await msg.edit_text("❌ Faqat ovozli xabar yuboring.")
            return

        audio_path = f"temp/auto_oby_{update.effective_user.id}_{int(time.time())}.{ext}"
        await audio_file.download_to_drive(audio_path)
        await msg.edit_text("⏳ Ovoz qabul qilindi. Qayta ishlanmoqda...")

        async def _bg(path: str):
            try:
                await process_obyektivka_from_audio_path(
                    context, path, update.effective_chat.id, update.effective_user.id
                )
            finally:
                try:
                    if path and os.path.exists(path):
                        os.remove(path)
                except Exception:
                    pass

        asyncio.create_task(_bg(audio_path))
        return
    except Exception as e:
        logger.error("auto_voice_obyektivka: %s", e, exc_info=True)
        try:
            await msg.edit_text(f"❌ Xatolik: {str(e)[:200]}")
        except Exception:
            pass
    finally:
        # Cleanup handled in background task
        pass
