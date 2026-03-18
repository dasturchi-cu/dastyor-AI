"""
AI Service Module - Google Gemini Integration (Async)
Handles Text Processing, Data Extraction, and Translation using Gemini Asynchronously.
"""
import logging
import json
import asyncio
from difflib import SequenceMatcher
import google.generativeai as genai
from config import GOOGLE_API_KEY

logger = logging.getLogger(__name__)

# Initialize Gemini
if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        logger.info("Google Gemini initialized successfully")
    except Exception as e:
        logger.error(f"Failed to init Gemini: {e}")

# Models to try in order (newest first — keeps working as Gemini releases progress)
GEMINI_MODELS = [
    'gemini-2.5-flash',
    'gemini-2.0-flash',
    'gemini-1.5-flash-latest',
]

_MODEL_CACHE = None
_MODEL_CACHE_NAME = None
_MODEL_CACHE_LOCK = asyncio.Lock()


async def get_model(preferred_models: list[str] | None = None):
    """Get Gemini model instance (cached) — tries models in order."""
    if not GOOGLE_API_KEY:
        return None

    global _MODEL_CACHE, _MODEL_CACHE_NAME
    order = preferred_models or GEMINI_MODELS

    # Fast path: cached model still matches preference list (or default list).
    if _MODEL_CACHE is not None and _MODEL_CACHE_NAME in order:
        return _MODEL_CACHE

    async with _MODEL_CACHE_LOCK:
        if _MODEL_CACHE is not None and _MODEL_CACHE_NAME in order:
            return _MODEL_CACHE

        for model_name in order:
            try:
                model = genai.GenerativeModel(model_name)
                _MODEL_CACHE = model
                _MODEL_CACHE_NAME = model_name
                logger.info(f"Using Gemini model: {model_name}")
                return model
            except Exception as e:
                logger.warning(f"Model {model_name} unavailable: {e}")

        logger.error("All Gemini models unavailable!")
        return None


GEMINI_TIMEOUT = 90  # seconds per API call

async def _gcall(coro, timeout: int = GEMINI_TIMEOUT):
    """Wrap generate_content_async with a hard timeout so the bot never hangs."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(f"Gemini API call timed out after {timeout}s")
        return None


def _set_para_text(para, text: str):
    """Set a Word paragraph's text safely (python-docx Paragraph has no .text setter)."""
    for run in para.runs:
        run.text = ''
    if para.runs:
        para.runs[0].text = text
    else:
        para.add_run(text)


def _set_pptx_paragraph_text(para, text: str):
    """
    Replace paragraph text while keeping at least one run style alive.
    """
    if para.runs:
        para.runs[0].text = text
        for run in para.runs[1:]:
            run.text = ""
    else:
        para.add_run().text = text


async def transcribe_audio(audio_file_path: str) -> str:
    """
    Transcribe audio using Gemini 3 Flash (Multimodal) asynchronously
    """
    if not GOOGLE_API_KEY:
        return ""
    
    loop = asyncio.get_running_loop()
    
    def blocking_upload():
        try:
            myfile = genai.upload_file(audio_file_path)
            # Wait for processing
            waited = 0
            while myfile.state.name == "PROCESSING" and waited < 30:
                import time
                time.sleep(2)
                waited += 2
                try:
                    myfile = genai.get_file(myfile.name)
                except:
                    break
            return myfile
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return None

    try:
        logger.info(f"Uploading audio file: {audio_file_path}")
        myfile = await loop.run_in_executor(None, blocking_upload)
        
        if not myfile:
            return "Audio yuklashda xatolik."
            
        if myfile.state.name == "FAILED":
            return "Audio faylni qayta ishlashda xatolik."
        
        model = await get_model()
        if not model: return "AI model xatosi."
        
        result = await _gcall(model.generate_content_async(
            [myfile, "Transcribe the speech in this audio to text accurately. Do not add any description, just the transcript."]
        ))

        # Cleanup (non-blocking)
        async def cleanup():
            try: genai.delete_file(myfile.name)
            except: pass
        asyncio.create_task(cleanup())

        if not result or not result.candidates:
            return "Audio tanilmadi."

        return result.text if result.text else "Bo'sh javob."

    except Exception as e:
        logger.error(f"Gemini Async Transcription error: {e}", exc_info=True)
        return "Audio transkripsiya xatoligi."


async def translate_document_gemini(file_path: str, target_language: str = "uz") -> str:
    """
    Translates a document using Gemini AI asynchronously.
    """
    if not GOOGLE_API_KEY:
        return ""
        
    try:
        from docx import Document
        
        # Doc processing is CPU bound, run in Executor
        loop = asyncio.get_running_loop()
        doc = await loop.run_in_executor(None, Document, file_path)
        
        model = await get_model()
        
        lang_map = {"uz": "Uzbek", "ru": "Russian", "en": "English"}
        target_lang_name = lang_map.get(target_language, "Uzbek")
        
        # Collect chunks
        full_text_chunks = []
        current_chunk = []
        current_length = 0
        
        for para in doc.paragraphs:
            if not para.text.strip(): continue
            if current_length + len(para.text) > 2000:
                full_text_chunks.append(current_chunk)
                current_chunk = []
                current_length = 0
            current_chunk.append(para)
            current_length += len(para.text)
            
        if current_chunk: full_text_chunks.append(current_chunk)
        
        # Add table cells as chunks
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        if para.text.strip():
                            full_text_chunks.append([para])

        logger.info(f"Translating doc: {len(full_text_chunks)} chunks to {target_lang_name}")

        async def translate_chunk(chunk):
            text = "\n\n".join([p.text for p in chunk])
            prompt = f"Translate to {target_lang_name}. Return ONLY text. Keep structure.\n\n{text}"
            try:
                resp = await _gcall(model.generate_content_async(prompt))
                return (resp.text if resp else None), chunk
            except Exception as e:
                logger.error(f"Chunk translation error: {e}")
                return None, chunk

        # Process in batches of 5
        for i in range(0, len(full_text_chunks), 5):
            batch = full_text_chunks[i:i+5]
            results = await asyncio.gather(*[translate_chunk(c) for c in batch])

            # Apply results — use _set_para_text (Paragraph.text has no setter in python-docx)
            for translated_text, original_paras in results:
                if translated_text and original_paras:
                    _set_para_text(original_paras[0], translated_text)
                    for p in original_paras[1:]:
                        _set_para_text(p, "")

            await asyncio.sleep(0.5)  # light pause to avoid rate limit

        # Save
        output_path = file_path.replace(".docx", f"_translated_{target_language}.docx")
        await loop.run_in_executor(None, doc.save, output_path)
        return output_path

    except Exception as e:
        logger.error(f"Async Doc Translation failed: {e}", exc_info=True)
        return ""


async def translate_text(text: str, direction: str = "uz_en") -> str:
    """
    Translate plain text using Gemini. Used by /api/translate web endpoint.
    direction: uz_en | en_uz | ru_uz | uz_ru | ru_en | en_ru
    """
    model = await get_model()
    if not model:
        return "AI model mavjud emas."

    lang_map = {
        "uz_en": ("O'zbek", "English"),
        "en_uz": ("English", "O'zbek"),
        "ru_uz": ("Russian", "O'zbek"),
        "uz_ru": ("O'zbek", "Russian"),
        "ru_en": ("Russian", "English"),
        "en_ru": ("English", "Russian"),
    }
    src, tgt = lang_map.get(direction, ("O'zbek", "English"))

    prompt = (
        f"Translate the following {src} text to {tgt}.\n"
        "Return ONLY the translated text, no explanations.\n\n"
        f"{text}"
    )
    try:
        resp = await _gcall(model.generate_content_async(prompt))
        if resp is None:
            return "Tarjima vaqti o'tdi. Iltimos, qayta urinib ko'ring."
        return resp.text.strip() if resp.text else "Natija bo'sh."
    except Exception as e:
        logger.error(f"translate_text error: {e}")
        return f"Tarjimada xato: {e}"


async def check_spelling_text(text: str) -> tuple[str, int]:
    """
    Spell-check plain text (Uzbek/Russian) using Gemini asynchronously.
    Returns: (corrected_text, fixes_count)
    """
    # Spellcheck should prioritize speed: try fastest models first.
    model = await get_model(preferred_models=[
        'gemini-2.0-flash',
        'gemini-2.5-flash',
        'gemini-1.5-flash-latest',
    ])
    if not model:
        return "AI model mavjud emas.", 0

    src = (text or "").strip()
    if not src:
        return "", 0

    # If there is nothing to fix (no letters), skip AI call.
    if not any(ch.isalpha() for ch in src):
        return src, 0

    # Keep a smaller timeout for spellcheck so UX feels snappy.
    spell_timeout = int((globals().get("GEMINI_SPELLCHECK_TIMEOUT") or 30))

    def _make_prompt(s: str) -> str:
        return (
            "Proofread ONLY obvious spelling mistakes (Uzbek/Russian).\n"
            "Return ONLY the corrected text.\n"
            "Fix typos, casing, and punctuation spacing.\n"
            "Do NOT rewrite style, sentence order, names, numbers, abbreviations, or meaning.\n"
            "If text is already correct, return it unchanged.\n"
            "No explanations.\n\n"
            f"{s}"
        )

    def _sanitize_spell_output(source: str, candidate: str) -> str:
        """
        Safety guard against hallucinated rewrites:
        keep the original if model output diverges too much.
        """
        cleaned = (candidate or "").strip()
        if not cleaned:
            return source
        ratio = SequenceMatcher(None, source, cleaned).ratio()
        # Conservative threshold: spelling fixes should remain close to original text.
        if ratio < 0.65:
            return source
        return cleaned

    try:
        # For long texts, split into chunks and process concurrently (faster + more reliable).
        if len(src) > 1600:
            parts: list[str] = []
            buf: list[str] = []
            cur = 0
            for para in src.splitlines():
                p = para.rstrip()
                # preserve blank lines
                if not p:
                    if buf:
                        parts.append("\n".join(buf).strip())
                        buf, cur = [], 0
                    parts.append("")
                    continue
                if cur + len(p) + 1 > 1200 and buf:
                    parts.append("\n".join(buf).strip())
                    buf, cur = [p], len(p)
                else:
                    buf.append(p)
                    cur += len(p) + 1
            if buf:
                parts.append("\n".join(buf).strip())

            # Process in small concurrent batches to avoid rate limits.
            out_parts: list[str] = []
            batch: list[str] = []
            for part in parts:
                if part == "":
                    out_parts.append("")
                    continue
                batch.append(part)
                if len(batch) >= 3:
                    resps = await asyncio.gather(*[
                        _gcall(
                            model.generate_content_async(
                                _make_prompt(x),
                                generation_config={"temperature": 0.0}
                            ),
                            timeout=spell_timeout
                        )
                        for x in batch
                    ])
                    for r, orig in zip(resps, batch):
                        out_parts.append(_sanitize_spell_output(orig, r.text if r and r.text else ""))
                    batch = []
            if batch:
                resps = await asyncio.gather(*[
                    _gcall(
                        model.generate_content_async(
                            _make_prompt(x),
                            generation_config={"temperature": 0.0}
                        ),
                        timeout=spell_timeout
                    )
                    for x in batch
                ])
                for r, orig in zip(resps, batch):
                    out_parts.append(_sanitize_spell_output(orig, r.text if r and r.text else ""))

            corrected = "\n".join(out_parts).strip()
        else:
            resp = await _gcall(
                model.generate_content_async(
                    _make_prompt(src),
                    generation_config={"temperature": 0.0}
                ),
                timeout=spell_timeout
            )
            corrected = _sanitize_spell_output(src, resp.text if resp else "")
            if not corrected:
                return src, 0

        # Heuristic: count changed segments (not exact, but gives a useful number)
        fixes = 0
        if corrected != src:
            # count differing words as an approximate "fix count"
            a = src.split()
            b = corrected.split()
            fixes = sum(1 for i in range(min(len(a), len(b))) if a[i] != b[i]) + abs(len(a) - len(b))
            fixes = max(1, min(fixes, 999))
        return corrected, fixes
    except Exception as e:
        logger.error(f"check_spelling_text error: {e}", exc_info=True)
        return src, 0


async def generate_objective(role: str, experience: str = "junior", extra: str = "", lang: str = "uz") -> str:
    """
    Generate a short professional CV objective/summary.
    lang: uz | ru | en
    experience: junior | middle | senior | lead
    """
    model = await get_model()
    if not model:
        return "AI model mavjud emas."

    l = (lang or "uz").lower().strip()
    if l not in ("uz", "ru", "en"):
        l = "uz"

    exp_map = {
        "junior": {"uz": "boshlang'ich", "ru": "начальный", "en": "junior"},
        "middle": {"uz": "o'rta", "ru": "средний", "en": "mid-level"},
        "senior": {"uz": "katta mutaxassis", "ru": "старший специалист", "en": "senior"},
        "lead":   {"uz": "rahbar", "ru": "руководитель", "en": "lead"},
    }
    exp_key = (experience or "junior").lower().strip()
    exp_label = exp_map.get(exp_key, exp_map["junior"])[l]

    # Keep it short and usable: 2–3 sentences, no bullet lists.
    if l == "ru":
        prompt = (
            "Сгенерируй краткую профессиональную цель (objective) для резюме.\n"
            "Требования: 2–3 предложения, без списков, без лишних объяснений, деловой стиль.\n"
            f"Должность: {role}\n"
            f"Уровень: {exp_label}\n"
            f"Дополнительно (если есть): {extra}\n"
        )
    elif l == "en":
        prompt = (
            "Generate a short professional resume objective.\n"
            "Requirements: 2–3 sentences, no bullet points, no extra explanation, professional tone.\n"
            f"Role: {role}\n"
            f"Level: {exp_label}\n"
            f"Extra (if any): {extra}\n"
        )
    else:
        prompt = (
            "Rezyume uchun qisqa professional obyektivka (objective) yozing.\n"
            "Talablar: 2–3 gap, ro'yxatsiz, ortiqcha izohsiz, rasmiy uslub.\n"
            f"Kasb/Lavozim: {role}\n"
            f"Daraja: {exp_label}\n"
            f"Qo'shimcha (bo'lsa): {extra}\n"
        )

    try:
        resp = await _gcall(model.generate_content_async(prompt))
        if resp is None:
            return "AI javobi kechikdi. Iltimos, qayta urinib ko'ring."
        return resp.text.strip() if resp.text else "Natija bo'sh."
    except Exception as e:
        logger.error(f"generate_objective error: {e}", exc_info=True)
        return f"Xatolik: {str(e)[:200]}"


async def extract_obyektivka_data(text: str) -> dict:
    """
    Extract structured data from text using Gemini asynchronously
    """
    model = await get_model()
    if not model: return {}
    
    prompt = f"""
    Quyidagi matndan shaxsiy ma'lumotlarni ajratib ber JSON formatida.
    Matn: {text}
    JSON struktura (HECH QANDAY MARKDOWNSIZ):
    {{
        "fullname": "Familiya Ism Sharif",
        "birthdate": "KK.OO.YYYY",
        "birthplace": "Viloyat, Tuman",
        "nation": "Millati",
        "party": "Partiyaviyligi",
        "education": "Ma'lumoti",
        "graduated": "Tamomlagan joyi va yili",
        "specialty": "Mutaxassisligi",
        "degree": "Ilmiy darajasi",
        "scientific_title": "Ilmiy unvoni",
        "languages": "Tillar",
        "military_rank": "Harbiy unvoni",
        "awards": "Mukofotlari", 
        "deputy": "Deputatligi",
        "work_experience": [{{"year": "Yillar", "position": "Ish joyi"}}],
        "relatives": [{{"degree": "Qarindoshligi", "fullname": "F.I.SH", "birth_year_place": "Tug'ilgan yili va joyi", "work_place": "Ish joyi", "address": "Yashash manzili"}}]
    }}
    """
    
    try:
        response = await _gcall(model.generate_content_async(prompt))
        if not response or not response.text:
            return {}
        cleaned = response.text.replace('```json', '').replace('```', '').strip()
        start = cleaned.find('{')
        end = cleaned.rfind('}') + 1
        if start != -1 and end != -1:
            cleaned = cleaned[start:end]
        return json.loads(cleaned)

    except Exception as e:
        logger.error(f"Async Data extraction error: {e}")
        return {}


async def check_spelling_gemini(file_path: str) -> tuple[str, int, int]:
    """
    Checks spelling in a DOCX file using Gemini asynchronously.
    Returns: (output_path, errors_found, errors_fixed)
    """
    if not GOOGLE_API_KEY:
        return "", 0, 0
        
    try:
        from docx import Document

        loop = asyncio.get_running_loop()
        doc = await loop.run_in_executor(None, Document, file_path)

        paragraphs_to_check = []
        for para in doc.paragraphs:
            if para.text and para.text.strip():
                paragraphs_to_check.append(para)

        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        if para.text and para.text.strip():
                            paragraphs_to_check.append(para)

        errors_fixed = 0

        async def process_para(para):
            src = para.text or ""
            corrected, fixes = await check_spelling_text(src)
            if corrected and corrected != src:
                _set_para_text(para, corrected)
                return max(1, fixes)
            return 0

        batch_size = 8
        for i in range(0, len(paragraphs_to_check), batch_size):
            batch = paragraphs_to_check[i:i + batch_size]
            errors_fixed += sum(await asyncio.gather(*[process_para(p) for p in batch]))
            await asyncio.sleep(0.15)

        output_path = file_path.replace(".docx", "_checked.docx")
        await loop.run_in_executor(None, doc.save, output_path)

        return output_path, errors_fixed, errors_fixed

    except Exception as e:
        logger.error(f"Async Spell check failed: {e}", exc_info=True)
        return "", 0, 0


async def check_spelling_pptx(file_path: str) -> tuple[str, int, int]:
    """
    Checks spelling in a PPTX file using Gemini asynchronously.
    Iterates slides → shapes → text frames → paragraphs → runs.
    Returns: (output_path, errors_found, errors_fixed)
    """
    if not GOOGLE_API_KEY:
        return "", 0, 0

    try:
        from pptx import Presentation

        loop = asyncio.get_running_loop()
        prs = await loop.run_in_executor(None, Presentation, file_path)

        paragraphs_to_check = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        if para.text and para.text.strip():
                            paragraphs_to_check.append(para)
                if shape.has_table:
                    for row in shape.table.rows:
                        for cell in row.cells:
                            for para in cell.text_frame.paragraphs:
                                if para.text and para.text.strip():
                                    paragraphs_to_check.append(para)

        errors_fixed = 0

        async def process_para(para):
            src = para.text or ""
            corrected, fixes = await check_spelling_text(src)
            if corrected and corrected != src:
                _set_pptx_paragraph_text(para, corrected)
                return max(1, fixes)
            return 0

        batch_size = 8
        for i in range(0, len(paragraphs_to_check), batch_size):
            batch = paragraphs_to_check[i:i + batch_size]
            errors_fixed += sum(await asyncio.gather(*[process_para(p) for p in batch]))
            await asyncio.sleep(0.15)

        output_path = file_path.replace(".pptx", "_checked.pptx")
        await loop.run_in_executor(None, prs.save, output_path)
        return output_path, errors_fixed, errors_fixed

    except Exception as e:
        logger.error(f"PPTX Spell check failed: {e}", exc_info=True)
        return "", 0, 0
