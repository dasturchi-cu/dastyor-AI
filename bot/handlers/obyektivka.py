from telegram import Update, InputFile, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
from bot.keyboards.reply_keyboards import get_back_button, get_main_menu
import os
import time
import logging
from bot.utils.progress import send_progress, update_progress
from bot.services.ai_service import transcribe_audio, extract_obyektivka_data
import json

WEBAPP_BASE = os.getenv("WEBAPP_BASE", "https://dastyor-ai.onrender.com/webapp")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

async def process_obyektivka_from_audio_path(context, audio_path, chat_id, user_id):
    """
    Core logic: Transcribe -> Extract Data -> Generate DOCX -> Send
    """
    # Initial Progress
    progress_msg = await send_progress(context, chat_id, "Audio tahlil qilinmoqda...")
    temp_docx = None
    
    try:
        await update_progress(context, progress_msg, 20, "Matn o'qilmoqda (Whisper)...")
        
        # 1. Transcribe
        transcribed_text = await transcribe_audio(audio_path)
        
        # Cleanup audio (optional, but good practice here if it was temp)
        # But caller might want to keep it. Let's not delete audio here. Or maybe we should?
        # Let caller handle audio deletion.
        
        if not transcribed_text:
            await progress_msg.edit_text("❌ Audio tushunarsiz. Iltimos, aniqroq gapiring.")
            return

        await update_progress(context, progress_msg, 50, "Ma'lumotlar ajratilmoqda (AI)...")
        
        # 2. Extract Data
        extracted_data = await extract_obyektivka_data(transcribed_text)
        
        if not extracted_data:
            await progress_msg.edit_text("❌ Ma'lumotlarni ajratib bo'lmadi. To'liqroq gapirib bering.")
            return
            
        summary = (
            f"✅ **Ma'lumotlar topildi:**\n"
            f"👤 {extracted_data.get('fullname', 'N/A')}\n"
            f"📅 {extracted_data.get('birthdate', 'N/A')}\n"
            f"📍 {extracted_data.get('birthplace', 'N/A')}\n"
            f"🎓 {extracted_data.get('education', 'N/A')}"
        )
        
        await update_progress(context, progress_msg, 80, "Web-shaklga bog'lanmoqda...")
        
        # 3. Save to JSON and generate Link
        os.makedirs("temp", exist_ok=True)
        json_path = f"temp/oby_data_{user_id}.json"
        
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(extracted_data, f, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving temp json: {e}")
        
        await update_progress(context, progress_msg, 100, "Tayyor!")
        
        # 4. Give webapp link
        kb = [[InlineKeyboardButton(
            "📋 Formani ko'rish / Yuklab olish", 
            web_app=WebAppInfo(url=f"{WEBAPP_BASE}/obyektivka.html?autoload=1&telegram_id={user_id}")
        )]]
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{summary}\n\n✅ **Ma'lumotlaringiz tayyorlandi.**\nQuyidagi havola orqali formani ko'rib chiqing va Word (DOCX) yoki PDF yuklab oling.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb)
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

    # Send example audio file
    # File is located in bot/handlers/ folder (same dir as this file)
    HANDLERS_DIR = os.path.dirname(os.path.abspath(__file__))
    audio_candidates = [
        os.path.join(HANDLERS_DIR, "speech (1).mp3"),   # bot/handlers/speech (1).mp3
        os.path.join(HANDLERS_DIR, "namuna.mp3"),        # bot/handlers/namuna.mp3
        os.path.join(BASE_DIR, "namuna.mp3"),            # project root fallback
    ]
    sent = False
    for path in audio_candidates:
        if os.path.exists(path):
            try:
                with open(path, 'rb') as af:
                    await update.message.reply_audio(
                        audio=InputFile(af, filename="namuna_audio.mp3"),
                        caption="🎙 *Namuna audio* — shunday qilib o'qib yuboring",
                        parse_mode="Markdown"
                    )
                sent = True
            except Exception as e:
                logger.warning(f"Could not send example audio ({path}): {e}")
            break
    if not sent:
        logger.warning(f"Example audio not found. Checked: {audio_candidates}")

    # Set user state
    context.user_data['waiting_for'] = 'obyektivka_audio'


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
        
        await msg.delete()
        
        # Process
        await process_obyektivka_from_audio_path(context, audio_path, update.effective_chat.id, update.effective_user.id)
        
    except Exception as e:
        logger.error(f"Upload Error: {e}")
        await msg.edit_text(f"❌ Yuklashda xato: {e}")
        
    finally:
        # Cleanup audio
        try:
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
        except: pass
        
        # Clear state handles by logic inside or caller?
        # Let's keep state unless back button pressed. BUT user might want to try again.
        # Usually we clear state only on success or back.
        # Let's leave it.
