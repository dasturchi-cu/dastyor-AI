from telegram import Update
from telegram.ext import ContextTypes
from bot.keyboards.reply_keyboards import get_back_button
import os
import logging

logger = logging.getLogger(__name__)

async def obyektivka_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle Obyektivka AI module.
    Opens Web App for intelligent resume/CV generation.
    """
    instruction_text = (
        "📄 **Obyektivka AI**\n\n"
        "Ushbu xizmat orqali siz:\n"
        "1️⃣ Audio xabar yuboring (malumotlaringizni o'qib bering)\n"
        "2️⃣ AI avtomatik ma'lumotlarni ajratadi\n"
        "3️⃣ Shablon to'ldiriladi va preview ko'rsatiladi\n"
        "4️⃣ DOCX va PDF formatda yuklab olasiz\n\n"
        "💡 **Maslahat:** Aniq va ravshan gapiring, shovqinli joyda yozishdan saqlaning.\n\n"
        "🎙 **Namuna:** 'Mening ismim Aliyev Ali, 1990-yil 15-mayda Toshkentda tug'ilganman...'\n\n"
        "Endi audio xabar yuboring."
    )
    
    await update.message.reply_text(
        instruction_text,
        reply_markup=get_back_button(),
        parse_mode="Markdown"
    )
    
    # Set user state to wait for audio
    context.user_data['waiting_for'] = 'obyektivka_audio'


async def handle_obyektivka_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process audio for obyektivka generation using OpenAI Whisper"""
    
    if not (update.message.voice or update.message.audio):
        await update.message.reply_text(
            "❌ Iltimos, audio xabar yuboring (voice yoki audio fayl)."
        )
        return
    
    await update.message.reply_text(
        "🎙 Audio qabul qilindi!\n\n"
        "⏳ Speech-to-Text jarayoni boshlandi...\n"
        "Iltimos, kuting (taxminan 10-30 soniya)."
    )
    
    try:
        # Get audio file
        if update.message.voice:
            audio_file = await update.message.voice.get_file()
            file_extension = "ogg"
        else:
            audio_file = await update.message.audio.get_file()
            file_extension = "mp3"
        
        # Download audio
        audio_path = f"temp_audio_{update.effective_user.id}.{file_extension}"
        await audio_file.download_to_drive(audio_path)
        
        # Transcribe using OpenAI Whisper
        from bot.services.ai_service import transcribe_audio, extract_obyektivka_data
        
        transcribed_text = await transcribe_audio(audio_path)
        
        # Clean up temp file (with retry)
        try:
            if os.path.exists(audio_path):
                time.sleep(0.5)  # Wait a bit before deletion
                os.remove(audio_path)
                logger.info(f"Deleted temp audio: {audio_path}")
        except Exception as cleanup_err:
            logger.warning(f"Could not delete temp file: {cleanup_err}")
        
        if not transcribed_text:
            await update.message.reply_text(
                "❌ Audio tanilmadi. Iltimos, qaytadan urinib ko'ring:\n"
                "• Aniqroq gapiring\n"
                "• Shovqinsiz joyda yozib oling\n"
                "• Audio sifatini yaxshilang"
            )
            return
        
        # Show transcribed text
        await update.message.reply_text(
            f"✅ Audio matnga o'tkazildi!\n\n"
            f"📝 **Matn:**\n{transcribed_text[:500]}{'...' if len(transcribed_text) > 500 else ''}\n\n"
            "⏳ Ma'lumotlar ajratilmoqda..."
        )
        
        # Extract structured data using GPT
        extracted_data = await extract_obyektivka_data(transcribed_text)
        
        if extracted_data:
            # Format extracted data for display
            summary = f"""
✅ **Ma'lumotlar ajratildi!**

👤 **FIO:** {extracted_data.get('fullname', 'N/A')}
📅 **Tug'ilgan:** {extracted_data.get('birthdate', 'N/A')}
📍 **Joyi:** {extracted_data.get('birthplace', 'N/A')}
🎓 **Ma'lumot:** {extracted_data.get('education', 'N/A')}

📄 Hujjat tayyorlanmoqda...
"""
            await update.message.reply_text(summary)
            
            # Generate DOCX document
            from bot.services.doc_generator import generate_obyektivka_docx
            
            await update.message.reply_text("📄 Hujjat generatsiya qilinmoqda...")
            
            try:
                docx_path = generate_obyektivka_docx(extracted_data)
                
                if os.path.exists(docx_path):
                    await update.message.reply_document(
                        document=open(docx_path, 'rb'),
                        caption="✅ Obyektivka tayyor (DOCX)",
                        filename=os.path.basename(docx_path)
                    )
                    # Cleanup
                    # os.remove(docx_path) # Keep for debugging if needed, or remove
                else:
                     await update.message.reply_text("❌ Hujjat yaratishda xatolik: fayl topilmadi")

            except Exception as e:
                logger.error(f"Doc gen error: {e}")
                await update.message.reply_text(f"❌ Hujjat yaratishda xatolik: {e}")
            
            await update.message.reply_text(
                "PDF versiyasi tez orada qo'shiladi.\n"
                "Yana biror xizmat kerakmi?",
                reply_markup=get_back_button()
            )
        else:
            await update.message.reply_text(
                "❌ Ma'lumotlarni ajratib bo'lmadi.\n"
                "Iltimos, to'liqroq ma'lumot bering va qaytadan urinib ko'ring."
            )
        
    except Exception as e:
        logger.error(f"Obyektivka audio processing error: {e}")
        await update.message.reply_text(
            "❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.\n"
            f"Xatolik: {str(e)[:100]}"
        )
    
    finally:
        # Clear state
        context.user_data.pop('waiting_for', None)
