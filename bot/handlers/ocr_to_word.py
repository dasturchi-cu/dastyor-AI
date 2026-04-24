"""
OCR to Word AI Handler (HTML Table Support)
"""
import os
import time
import logging
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from bot.keyboards.reply_keyboards import get_back_button, get_main_menu, get_ocr_to_word_keyboard
from bot.utils.helpers import is_back_button
from bot.services.plan_limits import CAT_OCR
from bot.services.user_service import get_user_lang, record_service_completion
from bot.services.usage_tracker import ensure_can_use_or_notify
from bot.utils.progress import send_progress, update_progress
from bot.utils.delivery import send_docx_with_confirmation

from services.ocr_service import extract_text
from services.docx_service import lines_to_docx

logger = logging.getLogger(__name__)

def _ocr_bot_extract_deadline_seconds() -> float:
    try:
        # Default increased to 180s to reduce "Timed out" for large scans.
        return float(max(45.0, float(os.getenv("OCR_BOT_EXTRACT_TOTAL_TIMEOUT_SECONDS", "180") or "180")))
    except Exception:
        return 180.0


def _ocr_bot_progress_pulse_seconds() -> float:
    try:
        v = float(os.getenv("OCR_BOT_PROGRESS_PULSE_SECONDS", "22") or "22")
        return max(0.0, min(120.0, v))
    except Exception:
        return 22.0


async def _extract_text_from_image_bot_timed(
    img_path: str,
    context,
    progress_msg,
    *,
    progress_pct: int,
    status_text: str,
) -> tuple[list[str], bool]:
    """
    OCR extract with hard deadline (avoids 3×Gemini = 3+ daqiqa 'qotib qolish').
    Returns (html_or_empty, timed_out).
    """
    deadline = _ocr_bot_extract_deadline_seconds()
    pulse_sec = _ocr_bot_progress_pulse_seconds()

    async def _pulse_loop() -> None:
        elapsed = 0.0
        try:
            while True:
                await asyncio.sleep(pulse_sec)
                elapsed += pulse_sec
                try:
                    await update_progress(
                        context,
                        progress_msg,
                        progress_pct,
                        f"{status_text} (hali ishlanmoqda, ~{int(elapsed)}s)",
                    )
                except Exception:
                    pass
        except asyncio.CancelledError:
            raise

    pulse_task: asyncio.Task | None = None
    if pulse_sec > 0:
        pulse_task = asyncio.create_task(_pulse_loop())
    timed_out = False
    extracted: list[str] = []
    resized_path: str | None = None
    using_resized = False

    def _maybe_downscale_for_ocr(path: str) -> str:
        """
        Downscale huge images to speed up OCR and prevent timeouts.
        Returns a path to use for OCR (original or resized temp copy).
        """
        try:
            from PIL import Image  # type: ignore

            max_side = int(os.getenv("OCR_BOT_MAX_SIDE", "1800") or "1800")
            if max_side < 800:
                max_side = 800
            im = Image.open(path)
            w, h = im.size
            if max(w, h) <= max_side:
                return path
            scale = max_side / float(max(w, h))
            nw = max(1, int(round(w * scale)))
            nh = max(1, int(round(h * scale)))
            im = im.convert("RGB")
            im = im.resize((nw, nh), Image.Resampling.LANCZOS)
            out_path = f"{path}.ocr_downscaled.jpg"
            im.save(out_path, format="JPEG", quality=85, optimize=True, progressive=True)
            return out_path
        except Exception:
            return path

    try:
        # Resize in thread (PIL is blocking).
        ocr_path = await asyncio.to_thread(_maybe_downscale_for_ocr, img_path)
        if ocr_path != img_path:
            resized_path = ocr_path
            using_resized = True
        extracted = await asyncio.wait_for(
            asyncio.to_thread(extract_text, ocr_path),
            timeout=deadline,
        )
        extracted = extracted or []
    except asyncio.TimeoutError:
        timed_out = True
        logger.warning(
            "OCR bot extract timeout after %.0fs path=%s",
            deadline,
            img_path,
        )
        extracted = []
    except Exception as e:
        logger.warning("OCR bot extract error path=%s: %s", img_path, e)
        extracted = []
    finally:
        if using_resized and resized_path and os.path.exists(resized_path):
            try:
                os.remove(resized_path)
            except Exception:
                pass
        if pulse_task is not None:
            pulse_task.cancel()
            try:
                await pulse_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
    return extracted, timed_out


def _schedule_ocr_auto_process(
    bot,
    chat_id: int,
    user_id: int,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """After the last photo, wait ~3s; if no new photos, start batch OCR (debounced)."""
    old = context.user_data.get("_ocr_debounce_task")
    if old and not old.done():
        old.cancel()

    async def _job():
        try:
            await asyncio.sleep(1.2)
            if context.user_data.get("waiting_for") != "ocr_image":
                return
            imgs = list(context.user_data.get("ocr_images") or [])
            if not imgs:
                return
            if not await ensure_can_use_or_notify(
                bot,
                chat_id,
                user_id,
                category=CAT_OCR,
                lang=get_user_lang(user_id),
            ):
                return
            context.user_data["ocr_images"] = []
            _run_ocr_batch_background(bot, chat_id, user_id, imgs, context.user_data)
            await bot.send_message(
                chat_id=chat_id,
                text=(
                    f"⏳ {len(imgs)} ta rasm avtomatik qayta ishlanmoqda.\n"
                    "Bir nechta rasm yuborganingizda, oxirgi rasmdan keyin ~1 soniya kutamiz."
                ),
            )
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.error("OCR debounce error: %s", e, exc_info=True)

    context.user_data["_ocr_debounce_task"] = asyncio.create_task(_job())


async def perform_ocr_and_send(context, image_path, chat_id, user_id):
    """
    Reusable function: Takes image path, performs OCR, creates Word doc, and sends it.
    Runs fully async; safe to call from a background task.
    """
    t0 = time.perf_counter()
    logger.info("OCR task started for user_id=%s chat_id=%s", user_id, chat_id)
    lang = get_user_lang(user_id)
    if not await ensure_can_use_or_notify(
        context.bot, chat_id, user_id, category=CAT_OCR, lang=lang
    ):
        return
    progress_msg = await send_progress(context, chat_id, "Jarayon boshlandi...")
    doc_path = None

    try:
        await update_progress(context, progress_msg, 20, "AI matnni o'qimoqda...")
        extracted_lines, timed_out = await _extract_text_from_image_bot_timed(
            image_path,
            context,
            progress_msg,
            progress_pct=20,
            status_text="AI matnni o'qimoqda...",
        )
        logger.info("OCR extract done in %.1fs user_id=%s", time.perf_counter() - t0, user_id)

        if not extracted_lines:
            if timed_out:
                await progress_msg.edit_text(
                    "⏱ **Vaqt tugadi** — rasm juda katta yoki server javobi sekin.\n\n"
                    "**Nima qilish mumkin:** jadvalni 2–3 qismga bo‘lib rasmga oling; "
                    "yorug‘roq va tekis surat yuboring.\n\n"
                    "Admin: `.env` da `OCR_BOT_EXTRACT_TOTAL_TIMEOUT_SECONDS=180`.",
                    parse_mode=ParseMode.MARKDOWN,
                )
            else:
                await progress_msg.edit_text("❌ **Xatolik:** Matn ajratilmadi.")
            return
            
        await update_progress(context, progress_msg, 70, "Word hujjat shakllantirilmoqda...")
        doc_path = f"Ocr_Natija_{user_id}_{int(time.time())}_@DastyorAiBot.docx"
        await asyncio.to_thread(lines_to_docx, extracted_lines, doc_path)
        
        await update_progress(context, progress_msg, 90, "Fayl yuborilmoqda...")
        
        # Send Document
        with open(doc_path, 'rb') as f:
            ok = await send_docx_with_confirmation(
                context.bot,
                chat_id,
                f,
                filename=doc_path,
                caption="✅ **Marhamat!**\n\nSizning hujjatingiz tayyor.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_menu(user_id, get_user_lang(user_id)),
            )
            if not ok:
                return

        record_service_completion(user_id, CAT_OCR, "OCR Image")
        await progress_msg.delete()
        # CLEAR STATE AFTER SUCCESS (when run from background task, user_data is shared)
        if getattr(context, "user_data", None) and context.user_data.get("waiting_for") == "ocr_image":
            context.user_data.pop("waiting_for", None)
        logger.info("OCR task completed in %.1fs user_id=%s", time.perf_counter() - t0, user_id)
    except Exception as e:
        logger.error("OCR Error user_id=%s: %s", user_id, e, exc_info=True)
        try:
            await progress_msg.edit_text(f"❌ **Xatolik yuz berdi:** {str(e)}")
        except Exception:
            pass
        
    finally:
        # Cleanup
        try:
            if doc_path and os.path.exists(doc_path):
                os.remove(doc_path)
        except Exception:
            logger.debug("OCR cleanup failed path=%s", doc_path, exc_info=True)


async def ocr_to_word_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start OCR process: collect images then process on 'Tayyor'."""
    context.user_data["waiting_for"] = "ocr_image"
    context.user_data["ocr_images"] = []
    uid = update.effective_user.id if update.effective_user else None
    lang = get_user_lang(uid) if uid else "uz_lat"

    msg = (
        "📜 **Hujjat rasmi → Word AI** ✨\n\n"
        "Rasmlarni yuboring (1–20 ta).\n"
        "Pastdagi **«✅ Tayyor — Word yaratish»** tugmasini bosing yoki *tayyor* deb yozing.\n"
        "Bitta yoki bir nechta rasm yuborganingizdan keyin ~3 soniya kutib, avtomatik ham boshlanadi."
    )
    await update.message.reply_text(
        msg,
        reply_markup=get_ocr_to_word_keyboard(lang),
        parse_mode=ParseMode.MARKDOWN,
    )


def _run_ocr_background(
    bot, chat_id: int, user_id: int, temp_image_path: str, user_data: dict
) -> None:
    """
    Run OCR in a fire-and-forget background task. Does NOT block the event loop.
    Cleans up temp file and updates user_data on completion.
    """
    async def _task():
        try:
            # Build a minimal context-like object for progress/send (no full Update)
            class _Ctx:
                def __init__(self, b, ud):
                    self.bot = b
                    self.user_data = ud
            ctx = _Ctx(bot, user_data)
            await perform_ocr_and_send(ctx, temp_image_path, chat_id, user_id)
        except Exception as e:
            logger.error(f"OCR background task failed: {e}", exc_info=True)
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ **OCR xatolik:** {str(e)}",
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                pass
        finally:
            try:
                if temp_image_path and os.path.exists(temp_image_path):
                    os.remove(temp_image_path)
            except Exception:
                pass

    asyncio.create_task(_task())


async def _perform_ocr_batch_and_send(context, bot, chat_id: int, user_id: int, file_ids: list) -> None:
    """
    Download all files, run OCR on each with progress (e.g. "Processing 3/10"),
    merge HTML into one Word doc, send. Runs in background; cleans up temp files.
    """
    t0 = time.perf_counter()
    n = len(file_ids)
    logger.info("OCR batch started user_id=%s chat_id=%s count=%s", user_id, chat_id, n)
    try:
        from bot.utils.system_tracker import track_event_fire_and_forget

        track_event_fire_and_forget(
            telegram_id=user_id,
            username=None,
            event_type="START",
            action_name="bot:ocr_batch",
            status="ok",
            metadata={"images": n},
        )
    except Exception:
        pass

    progress_msg = None
    temp_paths = []
    doc_path = None
    try:
        try:
            from bot.utils.system_tracker import track_span

            async with track_span(
                telegram_id=user_id,
                username=None,
                action_name="bot:ocr_batch",
                metadata={"images": n},
            ):
                pass
        except Exception:
            # span created in background; ignore
            pass

        progress_msg = await send_progress(context, chat_id, f"0/{n} — Yuklanmoqda...")
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        for i, fid in enumerate(file_ids):
            try:
                f = await bot.get_file(fid)
                ext = os.path.splitext(f.file_path or "")[1] or ".jpg"
                if not ext.startswith("."):
                    ext = "." + ext
                path = os.path.join(
                    temp_dir,
                    f"ocr_batch_{user_id}_{int(time.time())}_{i}{ext}",
                )
                await f.download_to_drive(path)
                temp_paths.append(path)
            except Exception as e:
                logger.warning("Batch download failed for file %s: %s", i, e)
        if not temp_paths:
            await progress_msg.edit_text("❌ Hech qanday rasm yuklanmadi.")
            return

        # 1 ta rasm bo'lsa batch yo'lga tushirmaymiz — tezroq single oqim.
        if len(temp_paths) == 1:
            img_path = temp_paths[0]
            await update_progress(context, progress_msg, 35, "AI matnni o'qimoqda...")
            extracted_lines, ocr_timed_out = await _extract_text_from_image_bot_timed(
                img_path,
                context,
                progress_msg,
                progress_pct=35,
                status_text="AI matnni o'qimoqda...",
            )

            # If OCR failed/empty: do NOT send image-only DOCX.
            # User expects text/table extraction only.
            if not extracted_lines:
                if ocr_timed_out:
                    await progress_msg.edit_text(
                        "⏱ **Vaqt tugadi** — jadval juda katta yoki rasm sifati past bo‘lishi mumkin.\n\n"
                        "**Sinab ko‘ring:** jadvalni bo‘laklab (2–4 rasm) yuboring, tekis va yorug‘ joyda oling.\n\n"
                        "Admin: `.env` da `OCR_BOT_EXTRACT_TOTAL_TIMEOUT_SECONDS=180` qilishingiz mumkin.",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                else:
                    await progress_msg.edit_text(
                        "❌ Matn ajratilmadi.\n\n"
                        "Jadval uchun rasmni iloji boricha tekis, yaqinroq va yorug' joyda oling.",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                return
            await update_progress(context, progress_msg, 80, "Word yaratilmoqda...")
            doc_path = f"Ocr_Natija_{user_id}_{int(time.time())}_@DastyorAiBot.docx"
            build_timeout = max(20, int(os.getenv("OCR_DOCX_BUILD_TIMEOUT_SECONDS", "90")))
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(lines_to_docx, extracted_lines, doc_path),
                    timeout=build_timeout,
                )
            except asyncio.TimeoutError:
                # Even fallback must never reference HTML/Gemini; write what we have.
                logger.warning(
                    "OCR single-from-batch DOCX timeout (%ss), saving minimal lines user=%s",
                    build_timeout,
                    user_id,
                )
                await asyncio.to_thread(lines_to_docx, extracted_lines, doc_path)

            await update_progress(context, progress_msg, 95, "Yuborilmoqda...")
            with open(doc_path, "rb") as f:
                ok_send = await send_docx_with_confirmation(
                    bot, chat_id, f,
                    filename=doc_path,
                    caption="✅ **Word fayl tayyor.**",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=get_main_menu(user_id, get_user_lang(user_id)),
                )
            if ok_send:
                record_service_completion(user_id, CAT_OCR, "OCR Single")
            await progress_msg.delete()
            if getattr(context, "user_data", None):
                context.user_data.pop("waiting_for", None)
                context.user_data.pop("ocr_images", None)
            return

        merged_lines: list[str] = []
        for i, img_path in enumerate(temp_paths):
            pct = 20 + int(70 * (i + 1) / len(temp_paths))
            await update_progress(
                context, progress_msg, pct,
                f"O'qilmoqda {i + 1}/{len(temp_paths)}...",
            )
            st = f"O'qilmoqda {i + 1}/{len(temp_paths)}"
            lines, _to = await _extract_text_from_image_bot_timed(
                img_path,
                context,
                progress_msg,
                progress_pct=min(90, pct),
                status_text=st,
            )
            if lines:
                merged_lines.extend(lines)
            else:
                merged_lines.append("[Matn ajratilmadi]")
            # Visual separation between images in the resulting doc
            if i < len(temp_paths) - 1:
                merged_lines.append("")

        await update_progress(context, progress_msg, 90, "Word yaratilmoqda...")
        doc_path = f"Ocr_Natija_{user_id}_{int(time.time())}_@DastyorAiBot.docx"
        await asyncio.to_thread(lines_to_docx, merged_lines, doc_path)

        await update_progress(context, progress_msg, 95, "Yuborilmoqda...")
        with open(doc_path, "rb") as f:
            ok_send = await send_docx_with_confirmation(
                bot, chat_id, f,
                filename=doc_path,
                caption="✅ **Barcha rasmlar bitta Word faylga birlashtirildi.**",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_menu(user_id, get_user_lang(user_id)),
            )
        if ok_send:
            record_service_completion(user_id, CAT_OCR, "OCR Batch")
        await progress_msg.delete()
        if getattr(context, "user_data", None):
            context.user_data.pop("waiting_for", None)
            context.user_data.pop("ocr_images", None)
        logger.info("OCR batch completed in %.1fs user_id=%s count=%s", time.perf_counter() - t0, user_id, n)
        try:
            from bot.utils.system_tracker import track_event_fire_and_forget

            track_event_fire_and_forget(
                telegram_id=user_id,
                username=None,
                event_type="END",
                action_name="bot:ocr_batch",
                status="success",
                execution_time_ms=int((time.perf_counter() - t0) * 1000),
                metadata={"images": n},
            )
        except Exception:
            pass
    except Exception as e:
        logger.error("OCR batch error user_id=%s: %s", user_id, e, exc_info=True)
        try:
            from bot.utils.system_tracker import track_event_fire_and_forget

            track_event_fire_and_forget(
                telegram_id=user_id,
                username=None,
                event_type="ERROR",
                action_name="bot:ocr_batch",
                status="failed",
                error_message=str(e)[:2000],
                execution_time_ms=int((time.perf_counter() - t0) * 1000),
                metadata={"images": n},
            )
        except Exception:
            pass
        try:
            if progress_msg:
                await progress_msg.edit_text(f"❌ **Xatolik:** {str(e)}")
        except Exception:
            pass
        if getattr(context, "user_data", None):
            context.user_data.pop("waiting_for", None)
            context.user_data.pop("ocr_images", None)
    finally:
        for p in temp_paths:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
        if doc_path:
            try:
                if os.path.exists(doc_path):
                    os.remove(doc_path)
            except Exception:
                pass


def _run_ocr_batch_background(bot, chat_id: int, user_id: int, file_ids: list, user_data: dict) -> None:
    """Start batch OCR in background; does not block the event loop."""
    class _Ctx:
        def __init__(self, b, ud):
            self.bot = b
            self.user_data = ud
    ctx = _Ctx(bot, user_data)

    async def _task():
        await _perform_ocr_batch_and_send(ctx, bot, chat_id, user_id, file_ids)

    asyncio.create_task(_task())


async def process_ocr_tayyor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Called when user says 'Tayyor' in OCR mode. Starts batch OCR in background.
    Returns True if batch was started, False otherwise.
    """
    images = context.user_data.get("ocr_images") or []
    if not images:
        return False
    t = context.user_data.get("_ocr_debounce_task")
    if t and not t.done():
        t.cancel()
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id if update.effective_user else 0
    if not await ensure_can_use_or_notify(
        context.bot,
        chat_id,
        user_id,
        category=CAT_OCR,
        lang=get_user_lang(user_id),
    ):
        return True
    context.user_data["ocr_images"] = []  # clear so we don't process twice
    _run_ocr_batch_background(context.bot, chat_id, user_id, images, context.user_data)
    await update.message.reply_text(
        f"⏳ {len(images)} ta rasm qayta ishlanmoqda. Natija tez orada yuboriladi.",
        parse_mode=ParseMode.MARKDOWN,
    )
    return True


async def handle_ocr_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle image upload (Direct menu usage). Downloads file then runs OCR in background."""
    message = update.message

    # Check if back button
    uid = update.effective_user.id if update.effective_user else None
    lang = get_user_lang(uid) if uid else "uz_lat"

    if message.text and is_back_button(message.text):
        context.user_data.pop("waiting_for", None)
        context.user_data.pop("ocr_images", None)
        t = context.user_data.get("_ocr_debounce_task")
        if t and not t.done():
            t.cancel()
        await update.message.reply_text(
            "🏠 **Asosiy menyuga qaytildi**",
            reply_markup=get_main_menu(uid, lang),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if not message.photo and not message.document:
        await update.message.reply_text(
            "⚠️ Iltimos, rasm yuboring (JPG yoki PNG formatda).",
            reply_markup=get_ocr_to_word_keyboard(lang),
        )
        return

    # Collect file_id (no download yet — batch will download on Tayyor)
    if message.document:
        mime = (message.document.mime_type or "").lower()
        fname = (message.document.file_name or "").lower()
        ok = mime.startswith("image/") or mime == "application/pdf" or fname.endswith(
            (".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf", ".heic", ".heif")
        )
        if mime and not ok:
            await update.message.reply_text(
                "⚠️ OCR uchun **rasm** (fotosurat sifatida) yoki **PDF** yuboring.\n"
                "Word/Excel fayllar bu yerda ishlamaydi.",
                reply_markup=get_ocr_to_word_keyboard(lang),
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        file_id = message.document.file_id
    else:
        file_id = message.photo[-1].file_id

    images = context.user_data.setdefault("ocr_images", [])
    if len(images) >= 20:
        await update.message.reply_text(
            "❌ Maksimum 20 ta rasm. *Tayyor* deb yozing yoki tugmani bosing.",
            reply_markup=get_ocr_to_word_keyboard(lang),
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    images.append(file_id)
    context.user_data["ocr_images"] = images

    await update.message.reply_text(
        f"✅ {len(images)} ta rasm qabul qilindi.\n\n"
        "Yana rasm yuboring, **Tayyor** tugmasini bosing yoki biroz kuting (avtomatik boshlanadi).",
        reply_markup=get_ocr_to_word_keyboard(lang),
        parse_mode=ParseMode.MARKDOWN,
    )
    _schedule_ocr_auto_process(
        context.bot,
        update.effective_chat.id,
        uid or 0,
        context,
    )
