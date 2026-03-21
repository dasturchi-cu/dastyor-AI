# LASHBOT — AI Hujjat Servis

Professional Telegram bot for document processing with AI capabilities.

## 🚀 Features

- ✨ **Obyektivka AI** - Intelligent resume generation via voice
- 📄 **Rasm → Word AI** - OCR with layout restoration
- 🔤 **Kirill-Lotin** - Uzbek transliteration
- 🌐 **Tarjima fayl** - Multi-language document translation
- 📑 **Rasm → PDF** - Image merging
- ✅ **Imlo tekshirish** - Spell checking
- 💎 **Premium xizmatlar** - Advanced features
- 💰 **Balans** - Payment integration
- ✉️ **Aloqa** - Support system

## 📦 Installation

```bash
# Clone repository
git clone <your-repo>
cd hujjatchi_ai_bot

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env and add your BOT_TOKEN
```

## ⚙️ Configuration

1. Get bot token from [@BotFather](https://t.me/BotFather)
2. Add token to `.env` file:
```
BOT_TOKEN=your_token_here
```

## 🏃 Run

**Telegram bot (polling, local dev):**

```bash
python main.py
```

**Production HTTP stack (WebApp static + REST `/api/*` + sync `/ocr` + Telegram webhook + Celery job routes):**

```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8000
# equivalent thin entry module:
uvicorn api_webhook:app --host 0.0.0.0 --port 8000
```

`backend.app` imports the same `app` instance built in `backend.server_app` (via `api_webhook.py`), so Docker and docs stay aligned.

Set `WEBAPP_BASE` to your public URL including `/webapp`, e.g. `https://your-host/webapp`, so Telegram opens `cv.html`, `ocr.html`, etc. A mismatch (API-only host without `/webapp`) causes WebApp “Not Found” / blank app.

## 📁 Project Structure

```
hujjatchi_ai_bot/
├── api_webhook.py          # ASGI entry (logging + create_webhook_app)
├── backend/
│   ├── app.py              # Re-exports `app` (same object as api_webhook)
│   ├── server_app.py       # Composes FastAPI: lifespan, routers, /webapp mount
│   ├── routers/            # site, public_web, ocr_web, documents_web, telegram_files_web, tg_update, jobs, ocr
│   ├── services/           # paddle_ocr_runtime, upload_io, temp_files, spellcheck_cache, …
│   ├── schemas/webapp.py   # Pydantic models for WebApp API
│   ├── tasks.py            # Celery → paddle_ocr_runtime
│   └── ...
├── bot/
│   ├── handlers/           # Telegram handlers
│   ├── keyboards/
│   ├── utils/
│   └── services/           # AI, OCR (Gemini), docs, sessions
├── webapp/                 # Telegram Web App (HTML/JS)
├── main.py                 # Polling bot + optional `RUN_MODE=api` OCR API
├── config.py
├── requirements.txt
└── .env
```

## 🔧 Tech Stack

- **Bot:** python-telegram-bot 21+
- **HTTP:** FastAPI + Uvicorn
- **OCR:** PaddleOCR (local, shared `backend/services/paddle_ocr_runtime.py`), Gemini path in `bot/services/ocr_service.py` for web “AI OCR”
- **Queue (optional):** Celery + Redis (`docker-compose.yml`)

## 📝 Todo

- [ ] Migrate `google.generativeai` → `google.genai`
- [ ] Payment gateway (Click, Payme) where needed

## 👨‍💻 Developer

Created with ❤️ using elite-level architecture.

## 📄 License

MIT
