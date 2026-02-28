import json
import logging
import os
from telegram import Update, InputFile
from telegram.ext import ContextTypes
from bot.services.doc_generator import generate_obyektivka_docx
import asyncio

logger = logging.getLogger(__name__)

async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles data sent from Web App via tg.sendData()
    """
    try:
        data_str = update.message.web_app_data.data
        payload = json.loads(data_str)
        
        action = payload.get("action")
        chat_id = update.effective_chat.id
        
        if action == "generate_obyektivka":
            await update.message.reply_text("⏳ Obektivka hujjati tayyorlanmoqda...")
            
            # Map the WebApp fields to the data expected by generate_obyektivka_docx
            # payload structure matches the generated JSON in webapp
            doc_data = {
                "fullname": payload.get("fullname", ""),
                "birthdate": payload.get("bdate", ""),
                "birthplace": payload.get("bplace", ""),
                "nation": payload.get("nation", ""),
                "party": payload.get("party", ""),
                "education": payload.get("edu", ""),
                "graduated": payload.get("grad", ""),
                "specialty": payload.get("spec", ""),
                "degree": payload.get("deg", ""),
                "scientific_title": payload.get("ttl", ""),
                "languages": payload.get("langs", ""),
                "military_rank": payload.get("mil", ""),
                "awards": payload.get("award", ""),
                "deputy": payload.get("dep", ""),
                "work_experience": [
                    {"year": f"{w.get('f', '')}-{w.get('t', '')}", "position": w.get('d', '')}
                    for w in payload.get("works", [])
                ],
                "relatives": [
                    {
                        "degree": r.get("type", ""),
                        "fullname": r.get("name", ""),
                        "birth_year_place": r.get("birth", ""),
                        "work_place": r.get("job", ""),
                        "address": r.get("addr", "")
                    }
                    for r in payload.get("rels", [])
                ]
            }
            
            temp_docx = await asyncio.to_thread(generate_obyektivka_docx, doc_data)
            
            if temp_docx and os.path.exists(temp_docx):
                with open(temp_docx, 'rb') as f:
                    await context.bot.send_document(
                        chat_id=chat_id,
                        document=InputFile(f, filename=os.path.basename(temp_docx)),
                        caption=f"✅ **Obyektivka tayyor!**\nSiz kiritgan ma'lumotlar asosida yaratildi.",
                        parse_mode="Markdown"
                    )
                try:
                    os.remove(temp_docx)
                except:
                    pass
            else:
                await update.message.reply_text("❌ Hujjat yaratishda xatolik yuz berdi.")

        elif action == "generate_cv":
            await update.message.reply_text("⏳ CV hujjati tayyorlanmoqda... (Tez kunda backend qo'shiladi)")
            # Here we can add generate_cv_docx later
            # For now just acknowledge
            
        else:
            await update.message.reply_text("❌ Noma'lum buyruq keldi.")

    except Exception as e:
        logger.error(f"WebApp Data Error: {e}", exc_info=True)
        await update.message.reply_text("❌ Ma'lumotlarni qabul qilishda xatolik.")
