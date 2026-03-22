import json
import logging
import os
import base64
import time
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from bot.services.doc_generator import generate_obyektivka_docx, generate_cv_docx, convert_to_pdf_safe
import asyncio
from bot.services.ai_service import check_spelling_text
from bot.handlers.premium import premium_handler
from bot.services.plan_limits import CAT_CV, CAT_OBYEKTIVKA, CAT_SPELL
from bot.services.usage_tracker import ensure_can_use_or_notify
from bot.services.user_service import get_user_lang, record_service_completion

logger = logging.getLogger(__name__)

def _generated_dir() -> str:
    base = "generated"
    os.makedirs(base, exist_ok=True)
    return base

async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles data sent from Web App via tg.sendData()
    """
    try:
        data_str = update.message.web_app_data.data
        payload = json.loads(data_str)
        
        action = payload.get("action")
        fmt = payload.get("format", "word").lower()
        chat_id = update.effective_chat.id
        
        if action == "generate_obyektivka":
            # Ob'yektivka bu bo'limda faqat Word (DOCX) ko'rinishida yuboriladi.
            fmt = "word"
            uid_oby = update.effective_user.id
            if not await ensure_can_use_or_notify(
                context.bot,
                chat_id,
                uid_oby,
                category=CAT_OBYEKTIVKA,
                lang=get_user_lang(uid_oby),
            ):
                return
            msg = await update.message.reply_text(f"⏳ Obyektivka ({fmt.upper()}) tayyorlanmoqda...")
            out_dir = _generated_dir()
            
            doc_data = {
                "lang": payload.get("lang", "uz_lat"),
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
                "current_job": payload.get("current_job", ""),
                "current_job_year": payload.get("current_job_year", ""),
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

            photo_path = None
            try:
                photo_data = payload.get("photo_data", "")
                if isinstance(photo_data, str) and photo_data.startswith("data:image/"):
                    header, b64 = photo_data.split(",", 1)
                    mime = header.split(";")[0].split(":")[1].lower()
                    ext = {
                        "image/png": "png",
                        "image/jpeg": "jpg",
                        "image/jpg": "jpg",
                        "image/webp": "webp",
                    }.get(mime, "png")
                    raw = base64.b64decode(b64)
                    ts = int(time.time() * 1000)
                    photo_path = os.path.join("temp", f"oby_webapp_photo_{ts}.{ext}")
                    with open(photo_path, "wb") as f:
                        f.write(raw)
            except Exception as e:
                logger.warning(f"web_app_data_handler photo decode failed: {e}")
                photo_path = None

            objective_path = os.path.join(out_dir, "objective.docx")
            temp_file = await asyncio.to_thread(generate_obyektivka_docx, doc_data, photo_path, out_dir)
            # Ensure stable filename requested by spec
            try:
                if temp_file and os.path.exists(temp_file) and temp_file != objective_path:
                    try:
                        os.replace(temp_file, objective_path)
                        temp_file = objective_path
                    except Exception:
                        # fallback to copy+remove if replace fails on Windows
                        import shutil
                        shutil.copyfile(temp_file, objective_path)
                        temp_file = objective_path
            except Exception:
                pass

        elif action == "generate_cv":
            uid_cv = update.effective_user.id
            if not await ensure_can_use_or_notify(
                context.bot,
                chat_id,
                uid_cv,
                category=CAT_CV,
                lang=get_user_lang(uid_cv),
            ):
                return
            msg = await update.message.reply_text(f"⏳ CV rezyume ({fmt.upper()}) tayyorlanmoqda...")
            out_dir = _generated_dir()
            temp_file = await asyncio.to_thread(generate_cv_docx, payload, out_dir)
            # Ensure stable filename requested by spec (docx)
            cv_docx = os.path.join(out_dir, "cv.docx")
            try:
                if temp_file and os.path.exists(temp_file) and temp_file != cv_docx:
                    try:
                        os.replace(temp_file, cv_docx)
                        temp_file = cv_docx
                    except Exception:
                        import shutil
                        shutil.copyfile(temp_file, cv_docx)
                        temp_file = cv_docx
            except Exception:
                pass
            
        elif action == "start_ocr":
            context.user_data['waiting_for'] = 'ocr_image'
            await update.message.reply_text("🖼 **Rasm→Word**: Menga rasm (yoki bir nechta rasm) yuboring. Men uni Word fayl qilib beraman.", parse_mode="Markdown")
            return
            
        elif action == "start_spellcheck":
            context.user_data['waiting_for'] = 'spellcheck_file'
            await update.message.reply_text("✏️ **Imlo tekshirish**: Menga matn, DOCX, yoki PPTX fayl yuboring. Xatolarni to'g'irlab beraman.", parse_mode="Markdown")
            return

        elif action == "spellcheck_text":
            txt = (payload.get("text") or "").strip()
            if not txt:
                await update.message.reply_text("Iltimos, tekshirish uchun matn yuboring.")
                return
            uid_sp = update.effective_user.id
            if not await ensure_can_use_or_notify(
                context.bot,
                chat_id,
                uid_sp,
                category=CAT_SPELL,
                lang=get_user_lang(uid_sp),
            ):
                return
            msg = await update.message.reply_text("⏳ Matn tekshirilmoqda...")
            corrected, fixes = await check_spelling_text(txt)
            await msg.delete()
            await update.message.reply_text(
                f"✅ Imlo tekshirish yakunlandi!\n\n"
                f"📊 Tuzatilgan: {fixes} ta o'zgarish\n\n"
                f"{corrected}"
            )
            record_service_completion(uid_sp, CAT_SPELL, "Spell WebApp sendData")
            return
            
        elif action == "start_img2pdf":
            context.user_data['waiting_for'] = 'pdf_images'
            context.user_data['pdf_images'] = []
            reply_markup = ReplyKeyboardMarkup([["✅ Tayyor", "❌ Bekor qilish"]], resize_keyboard=True)
            await update.message.reply_text("🖼 **Rasm→PDF**: Menga rasmlarni yuboring. Tugatgach, '✅ Tayyor' tugmasini bosing.", parse_mode="Markdown", reply_markup=reply_markup)
            return
            
        elif action == "start_translate":
            direction = payload.get("direction", "uz_en")
            context.user_data['translate_direction'] = direction
            context.user_data['waiting_for'] = 'translate_file'
            
            dir_str = direction.replace("_", " -> ").upper()
            await update.message.reply_text(f"🌐 **Tarjima fayl ({dir_str})**: \nMenga Word, PowerPoint yoki Excel fayl yuboring.", parse_mode="Markdown")
            return

        elif action == "premium_buy":
            # Premium purchase request from WebApp premium.html
            plan = str(payload.get("plan") or "premium").lower()
            if plan not in ("standard", "premium"):
                plan = "premium"
            context.user_data["premium_plan"] = plan
            context.user_data["waiting_for"] = "premium_payment_screenshot"
            await premium_handler(update, context)
            return
            
        elif action == "start_transliterate":
            direction = payload.get("direction", "k2l")
            d_map = {"k2l": "Kirill → Lotin", "l2k": "Lotin → Kirill"}
            context.user_data['translit_direction'] = direction
            context.user_data['waiting_for'] = 'translit_file'
            await update.message.reply_text(f"🔤 **Krill-Lotin ({d_map.get(direction, 'Kirill → Lotin')})**:\nMenga matn yoki hujjat yuboring.", parse_mode="Markdown")
            return
            
        else:
            await update.message.reply_text("❌ Noma'lum buyruq keldi.")
            return

        # Handle Format Conversion + Delivery (robust)
        if not temp_file or not os.path.exists(temp_file):
            await msg.edit_text("❌ Fayl yaratilmadi")
            return

        final_file = temp_file
        if fmt == "pdf":
            await msg.edit_text("⏳ PDF tayyorlanmoqda...")
            pdf_file = await asyncio.to_thread(convert_to_pdf_safe, temp_file, os.path.dirname(temp_file))
            if pdf_file and os.path.exists(pdf_file):
                # Ensure stable filename requested by spec
                stable_name = "cv_result.pdf"
                if action == "generate_obyektivka":
                    stable_name = "objective_result.pdf"
                cv_pdf = os.path.join(os.path.dirname(temp_file), stable_name)
                try:
                    if pdf_file != cv_pdf:
                        try:
                            os.replace(pdf_file, cv_pdf)
                            pdf_file = cv_pdf
                        except Exception:
                            import shutil
                            shutil.copyfile(pdf_file, cv_pdf)
                            pdf_file = cv_pdf
                except Exception:
                    pass
                final_file = pdf_file
            else:
                await msg.edit_text("⚠️ PDF yaratilmadi. Word format yuborilmoqda...")

        # STEP 1/2/5: ensure exists, send properly, handle errors
        if action == "generate_obyektivka":
            target_file = final_file
            if not target_file.lower().endswith(".pdf"):
                # Word expected
                objective_docx = os.path.join(_generated_dir(), "objective.docx")
                if os.path.isfile(objective_docx):
                    target_file = objective_docx

            if not os.path.isfile(target_file):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ Obyektivka fayli yaratilmadi",
                )
                return
            try:
                with open(target_file, "rb") as f:
                    await context.bot.send_document(chat_id=chat_id, document=f, caption="📄 Sizning faylingiz tayyor")
                if target_file.lower().endswith(".pdf"):
                    await context.bot.send_message(chat_id=chat_id, text="✅ Obyektivka PDF fayli botga yuborildi")
                else:
                    await context.bot.send_message(chat_id=chat_id, text="✅ Obyektivka Word fayli botga yuborildi")
                ok = True
            except Exception as e:
                logger.error("Obyektivka send failed: %s", e, exc_info=True)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ Obyektivka faylini yuborishda xatolik: {str(e)[:200]}",
                )
                ok = False
        elif action == "generate_cv":
            target_file = final_file
            if fmt == "pdf":
                expected_pdf = os.path.join(_generated_dir(), "cv_result.pdf")
                if os.path.isfile(expected_pdf):
                    target_file = expected_pdf
            if not os.path.isfile(target_file):
                await context.bot.send_message(chat_id=chat_id, text="❌ CV fayli yaratilmadi")
                return
            try:
                with open(target_file, "rb") as f:
                    await context.bot.send_document(chat_id=chat_id, document=f, caption="📄 Sizning faylingiz tayyor")
                if target_file.lower().endswith(".pdf"):
                    await context.bot.send_message(chat_id=chat_id, text="✅ CV PDF fayli botga yuborildi")
                else:
                    await context.bot.send_message(chat_id=chat_id, text="✅ CV Word fayli botga yuborildi")
                ok = True
            except Exception as e:
                logger.error("CV file send failed: %s", e, exc_info=True)
                if fmt == "pdf":
                    await context.bot.send_message(chat_id=chat_id, text=f"❌ CV PDF faylini yuborishda xatolik: {str(e)[:200]}")
                else:
                    await context.bot.send_message(chat_id=chat_id, text=f"❌ CV Word faylini yuborishda xatolik: {str(e)[:200]}")
                ok = False
        else:
            try:
                with open(final_file, "rb") as f:
                    await context.bot.send_document(chat_id=chat_id, document=f, caption="📄 Sizning faylingiz tayyor")
                ok = True
            except Exception as e:
                logger.error("Generic file send failed: %s", e, exc_info=True)
                await context.bot.send_message(chat_id=chat_id, text=f"❌ Fayl yuborilmadi: {str(e)[:200]}")
                ok = False

        if ok:
            await msg.delete()
            if action == "generate_cv":
                record_service_completion(update.effective_user.id, CAT_CV, "CV WebApp sendData")
            elif action == "generate_obyektivka":
                record_service_completion(update.effective_user.id, CAT_OBYEKTIVKA, "Obyektivka WebApp sendData")

        # Cleanup only transient webapp photo
        if action == "generate_obyektivka":
            try:
                if 'photo_path' in locals() and photo_path and os.path.exists(photo_path):
                    os.remove(photo_path)
            except Exception:
                pass

    except Exception as e:
        logger.error(f"WebApp Data Error: {e}", exc_info=True)
        await update.message.reply_text("❌ Ma'lumotlarni qabul qilishda xatolik.")
