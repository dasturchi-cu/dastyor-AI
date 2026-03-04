# DASTYOR AI — Website ↔ Telegram Bot Integration Architecture

> **Single unified platform.** Every website action is linked to the user's Telegram account.  
> Every generated file appears in **both** the browser download AND the Telegram chat.

---

## System Diagram

```
User opens Telegram bot
        │
        ▼
 /start command
        │  saves chat_id to user_profiles.json
        │  sends InlineKeyboard with WebApp buttons
        ▼
 Telegram Mini App (webapp/)
        │
        │  DastyorAI.init()  (app.js)
        │    1. reads Telegram.WebApp.initDataUnsafe.user
        │    2. falls back to ?telegram_id= URL param
        │    3. falls back to sessionStorage
        │    4. calls POST /api/auth → server session token
        │
        ▼
 Backend Server (api_webhook.py  +  FastAPI)
        │
        ├── Template Engine    →  bot/services/doc_generator.py
        ├── OCR Engine         →  bot/services/ocr_service.py
        ├── PDF Generator      →  bot/services/pdf_service.py
        ├── DOCX Generator     →  bot/services/doc_generator.py
        ├── Translation        →  bot/services/ai_service.py
        ├── Transliteration    →  bot/services/transliterate_service.py
        ├── Session Service    →  bot/services/session_service.py
        ├── User CRM           →  bot/services/user_service.py
        └── Telegram Bot       →  python-telegram-bot (PTB)
```

---

## Authentication Flow

```
1. User opens Mini App from Telegram bot button
2. Telegram injects initDataUnsafe.user into window.Telegram.WebApp
3. app.js reads user.id, first_name, username, photo_url
4. app.js calls POST /api/auth  { telegram_id, first_name, username, photo_url }
5. Server creates session token (32-char hex) in session_service.py
6. Server upserts user profile in user_service.py (with chat_id)
7. Token stored in sessionStorage under 'tg_token'
8. ALL subsequent API calls include ?token=<token> or Authorization header
9. Pages navigated to via DastyorAI.navigate() keep ?telegram_id= in URL
   so they also call /api/auth on first load
```

### Fallback chain (if Mini App SDK unavailable)
```
Telegram WebApp SDK  →  ?telegram_id= URL param  →  sessionStorage
```

---

## API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `POST /api/auth` | POST | Exchange Telegram identity → session token |
| `GET /api/me` | GET | Get user profile (token or telegram_id) |
| `GET /api/stats` | GET | Per-user usage statistics |
| `POST /api/notify` | POST | Send text notification to Telegram chat |
| `GET /api/bot-link` | GET | Generate deep-link for a bot command |
| `POST /api/translit` | POST | Cyrillic ↔ Latin conversion |
| `POST /api/translate` | POST | Text translation (UZ/EN/RU) |
| `POST /api/ocr_direct` | POST | Image → Word DOCX (+ Telegram send) |
| `POST /api/pdf_direct` | POST | Images → PDF (+ Telegram send) |
| `POST /api/generate_cv` | POST | **NEW** Form data → CV DOCX (+ Telegram send) |
| `POST /api/generate_obyektivka` | POST | **NEW** Form data → Obyektivka DOCX/PDF (+ Telegram send) |
| `POST /webhook` | POST | Telegram Bot incoming updates (PTB) |

---

## File Delivery System

Every generated file follows this dual-delivery pattern:

```python
# 1. Generate file in-memory (no disk unless unavoidable)
docx_bytes = build_document(payload)

# 2. Stream to browser (immediate download)
return StreamingResponse(io.BytesIO(docx_bytes), ...)

# 3. Background Telegram send (non-blocking)
asyncio.create_task(send_to_telegram(docx_bytes, chat_id))
```

This is implemented for:
- **OCR → Word** (`/api/ocr_direct`)
- **Images → PDF** (`/api/pdf_direct`)
- **CV Builder** (`/api/generate_cv`) ← New
- **Obyektivka** (`/api/generate_obyektivka`) ← New

---

## User Identity Persistence

`user_profiles.json` stores the following for every user:

```json
{
  "telegram_id": 123456789,
  "first_name": "Yusuf",
  "username": "yusuf_bot",
  "chat_id": 123456789,       ← NEW: persisted for file delivery
  "joined_at": "2026-01-01 12:00:00",
  "last_active": "2026-03-04 21:00:00",
  "files_processed": 42,
  "is_premium": false,
  "sessions": 5
}
```

`chat_id` is set by 3 codepaths:
1. `/start` command handler (first-ever bot interaction)
2. `track_user` middleware (every bot update)
3. `/api/auth` website endpoint (first webapp visit)

---

## Bot Commands

| Command | Action |
|---|---|
| `/start` | Welcome + full service menu with WebApp buttons |
| `/start cv` | Opens CV Builder directly |
| `/start obyektivka` | Opens Obyektivka Builder directly |
| `/start ocr` | Opens OCR tool directly |
| `/start pdf` | Opens Image→PDF tool directly |
| `/start translit` | Opens Transliteration tool directly |
| `/start translate` | Opens Translation tool directly |
| `/cv` | Opens CV Builder |
| `/obyektivka` | Opens Obyektivka Builder |
| `/ocr` | Opens OCR tool |
| `/pdf` | Opens Image→PDF tool |
| `/translit` | Opens Transliteration tool |
| `/translate` | Opens Translation tool |
| `/premium` | Opens Premium page |
| `/help` | Help information |

---

## Frontend SDK (webapp/app.js)

The `DastyorAI` namespace is loaded on every page:

```javascript
// Initialize and authenticate (call once on DOMContentLoaded)
const user = await DastyorAI.init();

// Get current user info
DastyorAI.getUser()          // { first_name, telegram_id, is_premium, ... }
DastyorAI.getTelegramId()    // string | null
DastyorAI.getToken()         // session token string | null

// Navigate while preserving telegram_id context
DastyorAI.navigate('cv.html')

// Send text notification to Telegram chat
DastyorAI.notify('CV tayyor!')

// Generate document + Telegram delivery + browser download
DastyorAI.generateDoc('/api/generate_cv', payload, 'MyCV.docx')

// Services
DastyorAI.translate(text, 'uz_en')
DastyorAI.translit(text, 'krill_to_lotin')

// Theme
DastyorAI.toggleTheme()
DastyorAI.isDark()

// i18n
DastyorAI.setLang('uz_lat')
DastyorAI.t('key')
```

---

## File Locations

```
hujjatchi_ai_bot/
├── api_webhook.py              ← FastAPI server + all /api/* endpoints
├── main.py                     ← Telegram bot setup (handlers, middleware)
├── config.py                   ← Environment variables
├── bot/
│   ├── handlers/
│   │   ├── start.py            ← /start + deep-link routing
│   │   ├── admin_middleware.py ← CRM tracking + chat_id persistence
│   │   ├── webapp_data.py      ← tg.sendData() handler (in-bot WebApp submit)
│   │   ├── ocr_to_word.py      ← Bot OCR handler
│   │   ├── obyektivka.py       ← Bot Obyektivka audio handler
│   │   └── ...
│   ├── services/
│   │   ├── user_service.py     ← CRM, chat_id, ban management
│   │   ├── session_service.py  ← Token-based auth sessions
│   │   ├── doc_generator.py    ← CV + Obyektivka DOCX generation
│   │   ├── ocr_service.py      ← Gemini OCR
│   │   ├── pdf_service.py      ← Image→PDF
│   │   ├── ai_service.py       ← Translation via Gemini
│   │   └── transliterate_service.py
│   └── keyboards/
│       └── reply_keyboards.py
└── webapp/
    ├── app.js                  ← DastyorAI SDK (shared by all pages)
    ├── i18n.js                 ← Internationalization system
    ├── theme.css               ← Global CSS design tokens
    ├── index.html              ← Home/dashboard
    ├── cv.html                 ← CV Builder
    ├── obyektivka.html         ← Obyektivka Builder
    ├── ocr.html                ← OCR tool
    ├── img2pdf.html            ← Image→PDF tool
    ├── translate.html          ← Translation tool
    ├── translit.html           ← Transliteration tool
    ├── premium.html            ← Premium info
    └── more.html               ← AI Tools hub
```

---

## Deployment Notes

- Server runs on **Render** at `https://dastyor-ai.onrender.com`
- Bot uses **webhook** mode (not polling) in production
- Static webapp files served at `/webapp/*` by FastAPI `StaticFiles`
- All generated files are in-memory — no permanent disk storage except `user_profiles.json` and `temp/sessions.json`
- Temp files in `temp/` are cleaned up immediately after use

---

*Last updated: 2026-03-04 by Antigravity integration engine*
