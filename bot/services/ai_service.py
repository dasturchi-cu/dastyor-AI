"""
AI Service Module - Google Gemini Integration (Async)
Handles Text Processing, Data Extraction, and Translation using Gemini Asynchronously.
"""
import logging
import json
import asyncio
import google.generativeai as genai
from config import GOOGLE_API_KEY
import os

logger = logging.getLogger(__name__)

# Initialize Gemini
if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        logger.info("Google Gemini initialized successfully")
    except Exception as e:
        logger.error(f"Failed to init Gemini: {e}")

# Models to try in order (gemini-2.0-flash is fastest & cheapest)
GEMINI_MODELS = [
    'gemini-2.0-flash',
    'gemini-1.5-flash',
    'gemini-1.5-pro',
]

async def get_model():
    """Get async Gemini model instance — tries models in order"""
    if not GOOGLE_API_KEY:
        return None
    # Try preferred model first, fall back if unavailable
    for model_name in GEMINI_MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            logger.info(f"Using Gemini model: {model_name}")
            return model
        except Exception as e:
            logger.warning(f"Model {model_name} unavailable: {e}")
    logger.error("All Gemini models unavailable!")
    return None


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
        
        result = await model.generate_content_async(
            [myfile, "Transcribe the speech in this audio to text accurately. Do not add any description, just the transcript."]
        )
        
        # Cleanup
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
                resp = await model.generate_content_async(prompt)
                return resp.text, chunk
            except Exception as e:
                logger.error(f"Chunk translation error: {e}")
                return None, chunk

        # Process in batches of 5 to respect rate limits
        for i in range(0, len(full_text_chunks), 5):
            batch = full_text_chunks[i:i+5]
            batch_tasks = [translate_chunk(c) for c in batch]
            results = await asyncio.gather(*batch_tasks)
            
            # Apply results
            for translated_text, original_paras in results:
                if translated_text:
                    if original_paras:
                        original_paras[0].text = translated_text
                        for p in original_paras[1:]:
                            p.text = ""
            
            # Rate limit pause
            await asyncio.sleep(2)

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
    direction: uz_en | en_uz | ru_uz | uz_ru | ru_en
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
    }
    src, tgt = lang_map.get(direction, ("O'zbek", "English"))

    prompt = (
        f"Translate the following {src} text to {tgt}.\n"
        "Return ONLY the translated text, no explanations.\n\n"
        f"{text}"
    )
    try:
        resp = await model.generate_content_async(prompt)
        return resp.text.strip() if resp and resp.text else "Natija bo'sh."
    except Exception as e:
        logger.error(f"translate_text error: {e}")
        return f"Tarjimada xato: {e}"


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
        response = await model.generate_content_async(prompt)
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
        
        # Load doc in thread (CPU bound)
        loop = asyncio.get_running_loop()
        doc = await loop.run_in_executor(None, Document, file_path)
        
        model = await get_model()
        
        # Collect paragraphs to check
        paragraphs_to_check = []
        for para in doc.paragraphs:
            if para.text.strip() and len(para.text.strip()) > 3:
                paragraphs_to_check.append(para)
                
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        if para.text.strip() and len(para.text.strip()) > 3:
                            paragraphs_to_check.append(para)
                            
        errors_found = 0
        errors_fixed = 0
        
        # Async chunk processor
        async def process_chunk(chunk):
            nonlocal errors_found, errors_fixed
            
            numbered_text = ""
            for idx, para in enumerate(chunk):
                numbered_text += f"[{idx}] {para.text}\n"
            
            prompt = f"""
            Proofread for Spelling errors (Uzbek/Russian).
            RULES:
            1. Return ONLY corrected lines in format '[N] Text'.
            2. If line is correct, return SAME line.
            3. Fix typos, casing, spaces. Do NOT change meaning.
            
            Text:
            {numbered_text}
            """
            
            try:
                resp = await model.generate_content_async(prompt)
                corrected_text = resp.text.strip()
                
                chunk_fixes = 0
                lines = corrected_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('[') and ']' in line:
                        bracket_end = line.index(']')
                        try:
                            idx = int(line[1:bracket_end])
                            new_text = line[bracket_end+1:].strip()
                            
                            if idx < len(chunk):
                                original_para = chunk[idx]
                                if original_para.text.strip() != new_text:
                                    chunk_fixes += 1
                                    if len(original_para.runs) == 1:
                                        original_para.runs[0].text = new_text
                                    else:
                                        original_para.text = new_text
                        except: pass
                return chunk_fixes
            except Exception as e:
                logger.error(f"Spell check chunk error: {e}")
                return 0

        # Process in batches
        chunk_size = 10
        tasks = []
        
        for i in range(0, len(paragraphs_to_check), chunk_size):
            chunk = paragraphs_to_check[i:i+chunk_size]
            tasks.append(process_chunk(chunk))
            
            if len(tasks) >= 2:
                results = await asyncio.gather(*tasks)
                errors_fixed += sum(results)
                tasks = []
                await asyncio.sleep(2)
        
        if tasks:
            results = await asyncio.gather(*tasks)
            errors_fixed += sum(results)

        errors_found = errors_fixed
        
        output_path = file_path.replace(".docx", "_checked.docx")
        await loop.run_in_executor(None, doc.save, output_path)
        
        return output_path, errors_found, errors_fixed
        
    except Exception as e:
        logger.error(f"Async Spell check failed: {e}", exc_info=True)
        return "", 0, 0
