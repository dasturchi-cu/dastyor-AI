"""
AI Service Module - Google Gemini Integration (Async)
Handles Text Processing, Data Extraction, and Translation using Gemini Asynchronously.
"""
import logging
import json
import asyncio
import os
import re
import httpx
import subprocess
import tempfile
import shutil
from concurrent.futures import ThreadPoolExecutor

from config.settings import settings
from features.ai.reliable import oby_extract_has_content, parse_json_object
from shared.ai_errors import AiQuotaError

logger = logging.getLogger(__name__)

# Dedicated thread pool for blocking ffmpeg/file I/O (keeps bot responsive)
_ai_executor = ThreadPoolExecutor(
    max_workers=int(os.getenv("AI_THREADPOOL_WORKERS", "4") or "4"),
    thread_name_prefix="ai",
)

GEMINI_TIMEOUT = settings.gemini_timeout  # seconds per API call
STT_SKIP_AUDIO_NORMALIZE = str(os.getenv("STT_SKIP_AUDIO_NORMALIZE", "0") or "0").strip().lower() in ("1", "true", "yes")


async def generate_text_with_fallback(
    prompt: str,
    *,
    preferred_models: list[str] | None = None,
    timeout: int = 35,
) -> str:
    """Multi-provider failover text generation (Gemini → OpenAI → OpenRouter → Groq → Cloudflare)."""
    from features.ai.routing import generate_text_with_failover

    try:
        return await generate_text_with_failover(
            prompt,
            preferred_models=preferred_models,
            timeout=timeout,
        )
    except AiQuotaError:
        raise
    except Exception as e:
        logger.error("AI failover generate error: %s", e)
        from shared.error_log import record_error

        record_error("ai_failover", str(e))
        raise


_STT_FAILURE_SUBSTRINGS = (
    "Audio yuklashda xatolik",
    "qayta ishlashda xatolik",
    "AI model xatosi",
    "Audio tanilmadi",
    "Bo'sh javob",
    "transkripsiya xatoligi",
)


def is_valid_transcription_text(text: str) -> bool:
    """True agar matn haqiqiy transkripsiya bo'lsa (xato xabari emas)."""
    t = (text or "").strip()
    if not t:
        return False
    u = t.upper()
    if u in ("[EMPTY]", "[BO'SH]", "[BOSH]"):
        return False
    if any(s in t for s in _STT_FAILURE_SUBSTRINGS):
        return False
    # Kamida 2 ta "belgi" (harf yoki raqam) — qisqa "ha" / "yo'q" ham o'tsin
    sig = sum(1 for ch in t if ch.isalnum())
    return sig >= 2


def _normalize_audio_for_gemini(src_path: str) -> tuple[str, bool]:
    """
    Telegram ovozi ko'pincha OGG/Opus. Gemini yuklashini yaxshilash uchun MP3 ga aylantiramiz.
    Qaytaradi: (yuklash uchun yo'l, vaqtinchalik fayl bo'lsa True).
    """
    src_path = os.path.abspath(src_path)
    if not os.path.isfile(src_path):
        return src_path, False
    ext = (os.path.splitext(src_path)[1] or "").lower()
    if ext in (".mp3", ".wav", ".mpeg", ".mpga", ".flac"):
        return src_path, False
    if not shutil.which("ffmpeg"):
        logger.debug("ffmpeg yo'q — audio asl formatda yuklanadi")
        return src_path, False
    fd, out_path = tempfile.mkstemp(suffix=".mp3", prefix="stt_")
    os.close(fd)
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                src_path,
                "-ac",
                "1",
                "-ar",
                "16000",
                "-codec:a",
                "libmp3lame",
                "-b:a",
                "64k",
                out_path,
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
        if os.path.isfile(out_path) and os.path.getsize(out_path) > 80:
            return out_path, True
    except Exception as e:
        logger.warning("ffmpeg audio normalize: %s", e)
    try:
        os.remove(out_path)
    except OSError:
        pass
    return src_path, False


_STT_PROMPT = (
    "Transcribe the speech in this audio to plain text. "
    "Preserve Uzbek (Latin or Cyrillic) as spoken; do not translate to English. "
    "If the audio is silent or unintelligible, reply with exactly: [EMPTY]. "
    "Otherwise output only the transcript, no labels or commentary."
)

_AUDIO_MIME_BY_EXT = {
    ".ogg": "audio/ogg",
    ".oga": "audio/ogg",
    ".opus": "audio/ogg",
    ".mp3": "audio/mp3",
    ".wav": "audio/wav",
    ".m4a": "audio/aac",
    ".aac": "audio/aac",
    ".flac": "audio/flac",
    ".webm": "audio/webm",
}


async def transcribe_audio(audio_file_path: str) -> str:
    """Speech-to-text via Gemini: one inline-audio request, failing over across Gemini keys."""
    from features.ai.gemini_rest import generate_content, inline_part, text_part
    from features.ai.routing.config import load_routing_config
    from features.ai.routing.cooldown import get_cooldown_registry
    from features.ai.routing.types import ProviderName

    cfg = load_routing_config()
    pcfg = cfg.providers.get(ProviderName.GEMINI)
    api_keys = list(pcfg.api_keys) if pcfg else []
    if not api_keys:
        return ""
    models = [m for m in pcfg.models if m.startswith("gemini")][:2] or ["gemini-2.5-flash"]

    loop = asyncio.get_running_loop()
    if STT_SKIP_AUDIO_NORMALIZE:
        upload_path, temp_conv = audio_file_path, False
    else:
        upload_path, temp_conv = await loop.run_in_executor(
            _ai_executor, _normalize_audio_for_gemini, audio_file_path
        )

    try:
        try:
            with open(upload_path, "rb") as fh:
                audio_bytes = await loop.run_in_executor(_ai_executor, fh.read)
        except OSError as e:
            logger.error("STT: audio read failed: %s", e)
            return "Audio yuklashda xatolik."
        if not audio_bytes:
            return "Audio yuklashda xatolik."

        ext = os.path.splitext(upload_path)[1].lower()
        parts = [
            inline_part(audio_bytes, _AUDIO_MIME_BY_EXT.get(ext, "audio/ogg")),
            text_part(_STT_PROMPT),
        ]
        cooldown = get_cooldown_registry(cfg.cooldown_ms)
        last_error = ""

        for key_index, api_key in enumerate(api_keys, start=1):
            if cooldown.is_cooling(ProviderName.GEMINI, key_index):
                continue
            for model in models:
                try:
                    result = await generate_content(
                        api_key, model, parts, timeout_sec=float(GEMINI_TIMEOUT), temperature=0.0
                    )
                except AiQuotaError as e:
                    last_error = str(e)
                    cooldown.set_cooldown(
                        ProviderName.GEMINI, key_index, duration_ms=cfg.cooldown_ms, reason="rate_limit"
                    )
                    break
                except Exception as e:
                    last_error = str(e) or type(e).__name__
                    logger.warning("STT failed key#%s model=%s: %s", key_index, model, last_error[:160])
                    continue

                raw = result.text
                if not raw:
                    if result.block_reason:
                        logger.warning("STT blocked: %s", result.block_reason)
                    return "Audio tanilmadi."
                if raw.upper() in ("[EMPTY]", "[BO'SH]", "[BOSH]"):
                    return ""
                logger.info("STT ok model=%s len=%s tokens=%s", model, len(raw), result.total_tokens)
                return raw

        logger.error("STT: all Gemini keys failed: %s", last_error[:200])
        from shared.error_log import record_error

        record_error("gemini", f"Transcription: {last_error[:300]}")
        return "Audio transkripsiya xatoligi."
    finally:
        if temp_conv:
            try:
                os.remove(upload_path)
            except OSError:
                pass


_TRANSLATE_FAILURE_MSGS = frozenset(
    {
        "Tarjima vaqtincha mavjud emas.",
        "Tarjima natijasi original bilan bir xil chiqdi.",
    }
)

_AI_GARBAGE_MARKERS = (
    "i'm ready to translate",
    "what is the o'zbek text",
    "what is the uzbek text",
    "please provide",
    "translate the following",
    "return only",
    "меня готовы перевести",
    "готов перевести",
    "готовы перевести",
    "какой текст",
    "что перевести",
    "что из узбекского",
    "какой текст из узбекского",
    "какой текст на узбекском",
    "я должен перевести",
    "должен перевести",
    "предоставьте текст",
    "переведите следующий",
    "qanday matn",
    "qaysi matnni",
    "tarjima qilishga tayyor",
)


def _none_for_direction(direction: str) -> str | None:
    if direction.endswith("_en"):
        return "none"
    if direction.endswith("_ru"):
        return "нет"
    return None


def _is_ai_garbage(text: str) -> bool:
    low = (text or "").strip().lower()
    if any(marker in low for marker in _AI_GARBAGE_MARKERS):
        return True
    if re.search(r"\b(none|нет)\s*$", low) and any(
        x in low for x in ("перевести", "translate", "matn", "текст", "text")
    ):
        return True
    return False


def is_ai_garbage(text: str) -> bool:
    """Public helper — detect meta-responses instead of real translations."""
    return _is_ai_garbage(text)


_DIRECTION_LANG_NAMES = {
    "uz_en": ("O'zbek", "English"),
    "en_uz": ("English", "O'zbek"),
    "ru_uz": ("Russian", "O'zbek"),
    "uz_ru": ("O'zbek", "Russian"),
    "ru_en": ("Russian", "English"),
    "en_ru": ("English", "Russian"),
}

_BATCH_TRANSLATE_MAX_ITEMS = 40
_BATCH_TRANSLATE_MAX_CHARS = 6000


async def _translate_json_chunk(texts: list[str], direction: str) -> list[str] | None:
    """Translate many strings in ONE request. None when the reply is unusable."""
    src, tgt = _DIRECTION_LANG_NAMES.get(direction, ("O'zbek", "English"))
    prompt = (
        f"Translate every string in this JSON array from {src} to {tgt}.\n"
        "Return ONLY a JSON array of strings with exactly the same number of items, "
        "in the same order. Keep numbers, dates, personal names and abbreviations. "
        "No explanations, no markdown.\n\n"
        + json.dumps(texts, ensure_ascii=False)
    )
    try:
        raw = await generate_text_with_fallback(prompt, timeout=GEMINI_TIMEOUT)
    except Exception as e:
        logger.warning("Batch translate failed (%s items): %s", len(texts), e)
        return None

    cleaned = (raw or "").replace("```json", "").replace("```", "").strip()
    start, end = cleaned.find("["), cleaned.rfind("]")
    if start == -1 or end <= start:
        return None
    try:
        parsed = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list) or len(parsed) != len(texts):
        logger.warning(
            "Batch translate size mismatch: sent=%s got=%s",
            len(texts),
            len(parsed) if isinstance(parsed, list) else "n/a",
        )
        return None
    if not all(isinstance(x, str) and x.strip() for x in parsed):
        return None
    return [x.strip() for x in parsed]


def _chunk_for_batch(indexes: list[int], texts: list[str]) -> list[list[int]]:
    chunks: list[list[int]] = []
    cur: list[int] = []
    cur_chars = 0
    for i in indexes:
        n = len(texts[i])
        if cur and (len(cur) >= _BATCH_TRANSLATE_MAX_ITEMS or cur_chars + n > _BATCH_TRANSLATE_MAX_CHARS):
            chunks.append(cur)
            cur, cur_chars = [], 0
        cur.append(i)
        cur_chars += n
    if cur:
        chunks.append(cur)
    return chunks


async def translate_strings_batch(
    texts: list[str],
    direction: str,
    *,
    concurrency: int = 4,
) -> list[str]:
    """Translate many strings: one AI request per chunk, per-string fallback if a chunk fails."""
    if not texts:
        return []

    from features.obyektivka.none_values import is_none_token

    out: list[str] = list(texts)
    pending: list[int] = []
    for i, src in enumerate(texts):
        if is_none_token(src):
            mapped = _none_for_direction(direction)
            if mapped is not None:
                out[i] = mapped
        elif (src or "").strip():
            pending.append(i)

    sem = asyncio.Semaphore(max(1, concurrency))

    async def _one(src: str) -> str:
        async with sem:
            res = await translate_text(src, direction=direction)
        if res == "Tarjima vaqtincha mavjud emas.":
            raise RuntimeError("translation_unavailable")
        if res in _TRANSLATE_FAILURE_MSGS:
            return src
        return res

    async def _chunk(idxs: list[int]) -> None:
        async with sem:
            translated = await _translate_json_chunk([texts[i] for i in idxs], direction)
        if translated is None:
            translated = list(await asyncio.gather(*[_one(texts[i]) for i in idxs]))
        for i, res in zip(idxs, translated):
            if _is_ai_garbage(res):
                logger.warning("AI garbage translation dropped for: %r -> %r", texts[i][:80], res[:120])
                continue
            out[i] = res

    await asyncio.gather(*[_chunk(c) for c in _chunk_for_batch(pending, texts)])
    return out


async def translate_text(text: str, direction: str = "uz_en") -> str:
    """
    Translate plain text using Gemini. Used by /api/translate web endpoint.
    direction: uz_en | en_uz | ru_uz | uz_ru | ru_en | en_ru
    """
    src, tgt = _DIRECTION_LANG_NAMES.get(direction, ("O'zbek", "English"))
    code_map = {
        "uz_en": ("uz", "en"),
        "en_uz": ("en", "uz"),
        "ru_uz": ("ru", "uz"),
        "uz_ru": ("uz", "ru"),
        "ru_en": ("ru", "en"),
        "en_ru": ("en", "ru"),
    }
    sl, tl = code_map.get(direction, ("uz", "en"))

    async def _google_fallback_translate(src_text: str, source_lang: str, target_lang: str) -> str:
        # Public translate endpoint fallback to keep service alive when Gemini quota is exhausted.
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": source_lang,
            "tl": target_lang,
            "dt": "t",
            "q": src_text,
        }
        timeout = httpx.Timeout(12.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        parts = []
        if isinstance(data, list) and data and isinstance(data[0], list):
            for item in data[0]:
                if isinstance(item, list) and item:
                    parts.append(str(item[0] or ""))
        return "".join(parts).strip()

    prompt = (
        f"Translate the following {src} text to {tgt}.\n"
        "Return ONLY the translated text, no explanations.\n\n"
        f"{text}"
    )
    try:
        out = await generate_text_with_fallback(prompt, timeout=GEMINI_TIMEOUT)
        if not out:
            out = await _google_fallback_translate(text, sl, tl)
        if not is_meaningfully_changed(text, out):
            return "Tarjima natijasi original bilan bir xil chiqdi."
        return out
    except Exception as e:
        logger.warning("Gemini translate failed, using fallback: %s", e)
        try:
            out = await _google_fallback_translate(text, sl, tl)
            if not out:
                return "Tarjima vaqtincha mavjud emas."
            if not is_meaningfully_changed(text, out):
                return "Tarjima natijasi original bilan bir xil chiqdi."
            return out
        except Exception as e2:
            logger.error("translate_text fallback error: %s", e2, exc_info=True)
            return "Tarjima vaqtincha mavjud emas."


def _normalize_for_compare(text: str) -> str:
    s = (text or "").strip().lower()
    # Normalize common apostrophe variants and whitespace.
    s = (
        s.replace("’", "'")
        .replace("`", "'")
        .replace("ʻ", "'")
        .replace("ʼ", "'")
        .replace("ʹ", "'")
    )
    s = re.sub(r"\s+", " ", s)
    return s


def is_meaningfully_changed(source: str, candidate: str) -> bool:
    a = _normalize_for_compare(source)
    b = _normalize_for_compare(candidate)
    if not a and not b:
        return False
    return a != b


def _oby_extract_has_content(d: dict) -> bool:
    return oby_extract_has_content(d)


async def extract_obyektivka_data(text: str) -> dict:
    """
    Extract structured data from text using Gemini asynchronously
    """
    prompt = f"""
    Quyidagi matndan obyektivka uchun faktlarni JSONga ajrat.
    Qoidalar:
    - Faqat aniq aytilgan ma'lumotni joylashtir, qolgani bo'sh.
    - fullname: "Familiya Ism Sharif" (imkon qadar).
    - work_experience: yillar "1977-1982 yy." yoki "2007-h.v." formatida; hozirgi ish boshlanish sanasi aniq bo'lsa "2007 yil 5 oktabrdan" ko'rinishida.
    - Hozirgi ish (h.v.) bo'lsa year maydonida "2007-h.v." yoki "2007 yil 5 oktabrdan" yoz; kun/oy aytilgan bo'lsa from_since yoki year ichida saqla (masalan "5 oktabr").
    - Javob faqat JSON bo'lsin (markdownsiz).

    Matn: {text}

    Faqat bitta JSON qaytar (markdown, ``` yo'q):
    {{
        "fullname": "Familiya Ism Sharif",
        "birthdate": "KK.OO.YYYY yoki bo'sh",
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
        raw_text = await generate_text_with_fallback(
            prompt,
            preferred_models=[
                "gemini-2.5-flash",
                "gemini-2.5-flash-lite",
            ],
            timeout=35,
        )
        if not raw_text:
            return {}
        parsed = parse_json_object(raw_text)
        if isinstance(parsed, dict) and _oby_extract_has_content(parsed):
            return parsed
        return {}

    except AiQuotaError:
        raise
    except Exception as e:
        logger.error(f"Async Data extraction error: {e}")
        return {}
