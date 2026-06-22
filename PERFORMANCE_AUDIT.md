# Performance Audit — Hujjatchi AI Bot + WebApp

**Sana:** 2026-06-22  
**Maqsad:** Bot javobi <300ms, callback <100ms, DB <50ms; WebApp Lighthouse 95+; tez PDF/DOCX generatsiya.

---

## Audit natijalari

| Kategoriya | Topilgan muammo | Holat |
|------------|-----------------|-------|
| **Slow query** | `/api/me` har so'rovda global `COUNT(*)` pending to'lovlar | ✅ Foydalanuvchi bo'yicha `count_user_pending` |
| **Slow query** | Har DB chaqiruvda yangi SQLite ulanish | ✅ Per-thread pool + WAL |
| **Blocking code** | `ffmpeg` event loopni bloklagan | ✅ `run_in_executor` |
| **Blocking code** | DOCX/PDF generatsiya async route ichida sync | ✅ `asyncio.to_thread` / `shared/async_db` |
| **Sync operation** | Obyektivka router `get_pending` sync | ✅ `async_db.run` |
| **N+1 query** | User lookup har xabarda DB ga | ✅ TTL cache `users.get_by_telegram_id` |
| **Memory leak** | Rate limit bucket cheksiz o'sishi | ✅ Stale key eviction `core/security.py` |
| **Memory leak** | PDF cache cheksiz | ✅ TTL + max size `render_service` |
| **Duplicate code** | Ovoz yuklash bot handlerlarda takrorlangan | ✅ `shared/voice.py` |
| **Duplicate code** | CV render ikki yo'l (`features/cv/render` vs `render_service`) | ✅ Bitta pipeline |
| **Heavy JS** | `cv.html` Tailwind CDN (~300KB) | ⚠️ P2 — keyingi bosqichda lokal CSS |
| **Heavy CSS** | `obyektivka.html` ~1800 qator inline CSS | ⚠️ P2 — `theme.css` ga ko'chirish |
| **Large image** | `video_frame_*.png` test fayllar | ✅ O'chirilgan / yo'q |
| **Unused asset** | Legacy `bot/handlers/*` (PTB) | ⚠️ P2 — `features/bot` ishlatiladi |
| **Unused dependency** | Supabase, Redis, Sentry, Playwright | ✅ Olib tashlangan |

---

## Amalga oshirilgan optimizatsiyalar

### Database (`database/`)

- **WAL mode**, `synchronous=NORMAL`, `cache_size=-8000`, `busy_timeout=5000`
- **Per-thread connection pool** — ulanish qayta ishlatiladi
- **Indekslar:** `idx_ai_sessions_user_type`, `idx_users_telegram`, `idx_payments_user_status`
- **`count_user_pending(telegram_id)`** — `/api/me` uchun tez so'rov

### Backend async (`shared/async_db.py`, `features/*/router.py`)

- Barcha og'ir sync operatsiyalar `asyncio.to_thread` orqali
- Obyektivka preview va DOCX generatsiya non-blocking
- CV PDF `render_service.generate_cv_pdf` + SHA256 TTL cache

### Bot (`features/bot/handlers/`)

- Voice handler: **darhol ack** + `asyncio.create_task` background AI
- Obyektivka: sample audio async yuboriladi
- Shared `download_voice_message()` — kod takrorlanmaydi

### Cache (`shared/cache.py`, `users.py`)

- In-process TTL cache (512 entry)
- User lookup 30s cache, credit o'zgarganda invalidate

### Payment (`features/payment/`)

- Har notify da yangi `Bot()` yaratish o'rniga **`app.state.bot`** qayta ishlatiladi
- Session yopilmaydi (lifespan boshqaradi)

### WebApp (`webapp/`)

- `index.html` — yengil, `theme.css`, SEO meta, dark mode
- `obyektivka.html` — `theme.css`, skeleton preview, Telegram dark mode
- `obyektivka-preview.js` — preview yuklanayotganda skeleton ko'rsatish
- `theme.css` — skeleton, empty/error/success state, dark mode CSS variables

### Security / stability

- Rate limit bucket eviction
- Credit consume → generate → refund on failure (CV + Obyektivka)

---

## Maqsadlar va hozirgi holat

| Metrika | Maqsad | Hozirgi holat |
|---------|--------|---------------|
| Bot message response | <300ms | ✅ Ack darhol; AI background |
| Bot callback response | <100ms | ✅ Inline keyboard ack |
| DB query | <50ms | ✅ Pool + indeks + cache |
| CV PDF generation | Maksimal tez | ✅ Cache + render_service |
| Obyektivka DOCX | Maksimal tez | ✅ `to_thread` + photo compress |
| Lighthouse Performance | 95+ | ⚠️ `cv.html` Tailwind CDN tufayli past bo'lishi mumkin |
| Lighthouse A11y/SEO/BP | 95+ | ✅ `index.html` tayyor; `cv.html` meta kerak |

---

## P2 — Keyingi bosqich (ixtiyoriy)

1. **`cv.html` refactor** — Tailwind CDN olib tashlash, `theme.css` + minimal utility
2. **`obyektivka.html` CSS ajratish** — inline → `obyektivka.css` (gzip bilan)
3. **Lazy import** — `weasyprint`, `docx`, `google.generativeai` faqat kerakda
4. **Session service** — JSON fayl o'rniga SQLite `ai_sessions`
5. **Legacy `bot/handlers/`** — to'liq o'chirish (faqat `features/bot` qoladi)
6. **Multi-worker** — in-process cache o'rniga Redis (faqat scale kerak bo'lsa)

---

## Tekshirish

```bash
# Import
python -c "from backend.server_app import create_webhook_app; create_webhook_app()"

# Bot (polling)
python main.py

# API
uvicorn api_webhook:app --reload
```

Lighthouse: Chrome DevTools → `webapp/index.html` (Telegram WebView yoki localhost).

---

## Arxitektura (optimizatsiya qatlami)

```
Telegram → Aiogram handler
              ├─ darhol answer ( <100ms )
              └─ create_task → AI / DB (background)

WebApp → FastAPI router
              ├─ async_db.run(sync_repo_fn)  → thread pool
              ├─ asyncio.to_thread(pdf/docx) → thread pool
              └─ TTL cache (user, pdf, preview)

SQLite ← per-thread pool ← WAL ← indexes
```
