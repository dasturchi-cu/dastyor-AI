import logging
import os
import time
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from bot.keyboards.inline_keyboards import (
    get_smart_photo_keyboard, get_smart_document_keyboard, get_smart_audio_keyboard
)
from bot.keyboards.reply_keyboards import get_image_to_pdf_keyboard, get_main_menu
from bot.handlers.ocr_to_word import perform_ocr_and_send
from bot.services.ai_service import transcribe_audio

logger = logging.getLogger(__name__)

async def handle_smart_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Smartly handle photo upload without menu selection"""
    
    # Save file ID temporarily
    file_id = update.message.photo[-1].file_id if update.message.photo else update.message.document.file_id
    context.user_data['smart_file_id'] = file_id
    context.user_data['smart_file_type'] = 'photo'
    
    msg = (
        "🤖 **Aqlli Yordamchi:** Rasm qabul qilindi!\n\n"
        "Nima qilishni xohlaysiz? Quyidagi varianlardan birini tanlang:"
    )
    
    await update.message.reply_text(
        msg, 
        reply_markup=get_smart_photo_keyboard(),
        parse_mode="Markdown"
    )

async def handle_smart_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Smartly handle document upload"""
    
    doc = update.message.document
    file_ext = os.path.splitext(doc.file_name)[1].lower() if doc.file_name else ""
    
    # Save file ID
    context.user_data['smart_file_id'] = doc.file_id
    context.user_data['smart_file_type'] = 'document'
    context.user_data['smart_file_ext'] = file_ext
    context.user_data['smart_file_name'] = doc.file_name
    
    msg = (
        f"🤖 **Aqlli Yordamchi:** Hujjat qabul qilindi (`{doc.file_name}`)!\n\n"
        "Qanday amal bajaramiz?"
    )
    
    await update.message.reply_text(
        msg, 
        reply_markup=get_smart_document_keyboard(file_ext),
        parse_mode="Markdown"
    )

async def handle_smart_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Smartly handle audio/voice upload"""
    
    # Save file ID
    file_id = update.message.voice.file_id if update.message.voice else update.message.audio.file_id
    context.user_data['smart_file_id'] = file_id
    context.user_data['smart_file_type'] = 'audio'
    
    msg = (
        "🤖 **Aqlli Yordamchi:** Audio xabar keldi!\n\n"
        "Uni matnga aylantiraymi yoki obyektivka to'ldiramizmi?"
    )
    
    await update.message.reply_text(
        msg, 
        reply_markup=get_smart_audio_keyboard(),
        parse_mode="Markdown"
    )

async def smart_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from smart keyboards"""
    query = update.callback_query
    data = query.data
    
    # Answer callback
    await query.answer()
    
    if data == "smart_cancel":
        if 'smart_file_id' in context.user_data: del context.user_data['smart_file_id']
        await query.message.edit_text("🚫 Bekor qilindi.")
        return

    # Check if file exists in context
    file_id = context.user_data.get('smart_file_id')
    if not file_id:
        await query.message.edit_text("⚠️ Fayl sessiyasi tugagan. Iltimos, qayta yuboring.")
        return
        
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    temp_path = None
    
    try:
        # === 1. OCR (Rasm -> Word) ===
        if data == "smart_ocr":
            await query.message.edit_text("⏳ Yuklanmoqda...")
            
            # Download file
            file_obj = await context.bot.get_file(file_id)
            temp_path = f"smart_ocr_{user_id}_{int(time.time())}.jpg"
            await file_obj.download_to_drive(temp_path)
            
            # Delete menu message
            await query.message.delete()
            
            # Perform OCR (using shared logic)
            await perform_ocr_and_send(context, temp_path, chat_id, user_id)
            return

        # === 2. Image -> PDF ===
        elif data == "smart_img2pdf":
            # Initialize or retrieve existing PDF session
            pdf_images = context.user_data.get("pdf_images", [])
            pdf_images.append(file_id)
            context.user_data["pdf_images"] = pdf_images
            context.user_data["waiting_for"] = "pdf_images"
            
            # Delete "Smart Menu" message
            await query.message.delete()
            
            # Send standard "Image to PDF" interface
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"✅ Rasm PDF ro'yxatiga qo'shildi ({len(pdf_images)} ta).\n\n"
                    "Yana rasm yuboring (ketma-ket) yoki tayyor bo'lsa **'Tayyor'** tugmasini bosing."
                ),
                reply_markup=get_image_to_pdf_keyboard(),
                parse_mode="Markdown"
            )
            return

        # === 3. Transcribe (Audio -> Text) ===
        elif data == "smart_transcribe":
            await query.message.edit_text("⏳ Audio yuklanmoqda va transkripsiya qilinmoqda...")
            
            # Download file
            file_obj = await context.bot.get_file(file_id)
            temp_path = f"smart_audio_{user_id}_{int(time.time())}.ogg"
            await file_obj.download_to_drive(temp_path)
            
            # Transcribe
            text = await transcribe_audio(temp_path)
            
            # Send result
            await query.message.delete()
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"📝 **Transkripsiya:**\n\n{text}",
                parse_mode="Markdown",
                reply_markup=get_main_menu(update.effective_user.id if update.effective_user else None)
            )
            return

        # === 4. Obyektivka (Audio -> Obyektivka) ===
        elif data == "smart_obyektivka_audio":
            # Pass to Obyektivka handler logic
            # Since obyektivka handler is complex (state machine), we might need to "fake" it or call a service.
            # For now, let's keep it simple: Just transcribe and say "Here is text, you can copy it to Obyektivka menu".
            # Or better: Set state to 'obyektivka_audio' -> but we already have the file.
            
            # Let's use internal logic:
            from bot.handlers.obyektivka import process_obyektivka_from_audio_path
            
            await query.message.edit_text("⏳ Audio tahlil qilinmoqda...")
             # Download file
            file_obj = await context.bot.get_file(file_id)
            temp_path = f"smart_oby_audio_{user_id}_{int(time.time())}.ogg"
            await file_obj.download_to_drive(temp_path)
            
            await query.message.delete()
            await process_obyektivka_from_audio_path(context, temp_path, chat_id, user_id)
            return
            
        # === 5. Translate (Doc → Doc) — Step 1: choose direction ===
        elif data == "smart_translate":
            from bot.keyboards.inline_keyboards import get_smart_translate_keyboard
            await query.message.edit_text(
                "🌍 <b>Tarjima yo'nalishini tanlang:</b>",
                parse_mode="HTML",
                reply_markup=get_smart_translate_keyboard()
            )
            return

        # === 5b. Translate — Step 2: direction chosen, do translation ===
        elif data.startswith("smart_trl_"):
            direction = data.replace("smart_trl_", "")  # e.g. 'ru_uz'
            DIRECTION_LABELS = {
                'ru_uz': "Rus → O'zbek", 'uz_ru': "O'zbek → Rus",
                'en_uz': "Ingliz → O'zbek", 'uz_en': "O'zbek → Ingliz",
            }
            TARGET_LANG = {'ru_uz': 'uz', 'uz_ru': 'ru', 'en_uz': 'uz', 'uz_en': 'en'}
            label = DIRECTION_LABELS.get(direction, direction)
            target_lang = TARGET_LANG.get(direction, 'uz')

            file_name = context.user_data.get('smart_file_name', 'document.docx')
            ext = os.path.splitext(file_name)[1].lower()

            if ext not in ('.docx',):
                await query.message.edit_text(
                    f"❌ <b>{ext}</b> formati qo'llab-quvvatlanmaydi.\n"
                    "Faqat <b>.docx</b> (Word) tarjima qilinadi.",
                    parse_mode="HTML"
                )
                return

            await query.message.edit_text(
                f"⏳ <b>'{file_name}'</b> tarjima qilinmoqda...\n"
                f"🔄 {label} · AI ishlamoqda (30–90 son).",
                parse_mode="HTML"
            )

            temp_path = f"smart_trl_{user_id}_{int(time.time())}{ext}"
            translated_path = None
            try:
                from telegram import InputFile
                from bot.services.ai_service import translate_document_gemini

                file_obj = await context.bot.get_file(file_id)
                await file_obj.download_to_drive(temp_path)

                translated_path = await translate_document_gemini(temp_path, target_lang)

                if translated_path and os.path.exists(translated_path):
                    base_name = os.path.splitext(file_name)[0]
                    out_name = f"{base_name}_{target_lang}_@DastyorAiBot{ext}"
                    await query.message.delete()
                    with open(translated_path, "rb") as fp:
                        await context.bot.send_document(
                            chat_id=chat_id,
                            document=InputFile(fp, filename=out_name),
                            caption=(
                                f"✅ <b>Tarjima tayyor!</b>\n"
                                f"📄 Original: <code>{file_name}</code>\n"
                                f"🔄 {label}\n"
                                f"📎 <code>{out_name}</code>"
                            ),
                            parse_mode="HTML"
                        )
                else:
                    await query.message.edit_text(
                        "❌ Tarjima qilishda xatolik yuz berdi.\n"
                        "Fayl bo'sh yoki murakkab tuzilmaga ega bo'lishi mumkin."
                    )
            except Exception as trl_err:
                logger.error(f"Smart translate error: {trl_err}", exc_info=True)
                await query.message.edit_text(f"❌ Xatolik: {str(trl_err)[:120]}")
            finally:
                for p in [temp_path, translated_path]:
                    if p and os.path.exists(p):
                        try: os.remove(p)
                        except: pass
            return

        # ... other handlers ...
        
        await query.message.edit_text(f"✅ Tanlandi: {data}. (Ishlanmoqda...)")
        
    except Exception as e:
        logger.error(f"Smart Callback Error: {e}", exc_info=True)
        await query.message.edit_text(f"❌ Xatolik: {e}")
        
    finally:
        # Cleanup
        if temp_path and os.path.exists(temp_path):
            try: os.remove(temp_path)
            except: pass
