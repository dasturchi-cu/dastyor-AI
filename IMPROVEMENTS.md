# Dastyor AI — Optimization & Improvement Report

**Date:** 2026-06-08  
**Scope:** Performance, watermark workflow, UI/UX, Uzbek localization, security, code quality

---

## 1. Identified Issues (Before)

| Area | Issue | Severity |
|------|-------|----------|
| Security | `/api/export_cv` and `/api/export_obyektivka` allowed clean exports **without authentication** when `telegram_id`/`token` omitted | Critical |
| Security | Preview API accepted `watermark: false` from client — potential PII leak | High |
| Performance | Playwright launched **new Chromium per PDF** (~2–5s cold start each request) | High |
| Performance | Missing `webapp/locales/uz.json` caused failed fetch on every page load | Medium |
| Performance | Large base64 photos stored uncompressed in `paid_doc_requests` | Medium |
| UX | Watermark text (`@DastyorAiBot`) was subtle; no prominent “DEMO” banner | Medium |
| Localization | Locale files missing; `ru`/`en` paths fetched but unused (bot is Uzbek-only) | Medium |
| Bot UX | Inline menu lacked quick access to document history | Low |

---

## 2. Performance Improvements Implemented

### Bot & API
- **Playwright browser pool** (`bot/services/render_service.py`): reuses warm Chromium across PDF renders; recycles after `PLAYWRIGHT_BROWSER_MAX_USES` (default 40).
- **Obyektivka preview cache TTL** increased 45s → 60s; template revision bumped to invalidate stale HTML after watermark update.
- **Server-side photo compression** before DB save (`compress_payload_photo`) — shrinks payloads ~70–90% for typical passport photos.
- **Inline Uzbek locale fallback** in `webapp/app.js` — zero network dependency on cold start if JSON fetch fails.
- **Locale fetch timeout** reduced 3000ms → 1500ms for faster perceived load.

### Expected impact (typical deployment)
| Operation | Before | After (est.) |
|-----------|--------|--------------|
| Obyektivka test PDF (2nd+ request) | 4–8s | 1.5–3s |
| WebApp first paint (i18n) | +1 failed fetch | Instant fallback |
| Paid request DB write (with photo) | 200–800 KB payload | 30–80 KB payload |

---

## 3. Watermark Workflow (Preview → Payment → Premium)

### Already existed (preserved)
1. Form fill → data stored in `paid_doc_requests` (Supabase)
2. Live preview via `/api/preview_obyektivka`
3. Manual card payment + screenshot → admin approve
4. Clean Word/PDF export after payment

### Enhancements added
| Step | Change |
|------|--------|
| Preview | **Forced** `watermark=true` + `mask_pii=true` server-side (client cannot disable) |
| Visual | Red **“DEMO VERSIYA — FAQAT KO'RISH UCHUN”** banner on document |
| Tiled WM | Default text: `DEMO VERSIYA · @DastyorAiBot` (env-configurable) |
| Test PDF | Filename prefix `DEMO_Malumotnoma_*` |
| Config | `DOC_WATERMARK_TEXT`, `DOC_PREVIEW_BANNER_TEXT`, `DOC_WATERMARK_OPACITY` in `.env` |

### Payment flow (unchanged logic, hardened)
```
Form → save to DB → demo preview (watermarked)
     → pay 5 000 UZS + screenshot → admin approve
     → clean export (auth + quota required)
     → re-download via /docs or paid_doc_status
```

---

## 4. UI/UX Improvements

- **WebApp theme.css**: loading spinner, success/error toast styles, form validation visual states.
- **Obyektivka preview note**: clearer Uzbek explanation of demo vs paid version.
- **Bot welcome/help**: mentions demo preview before payment.
- **Inline keyboard**: added “📂 Mening hujjatlarim” for faster navigation.
- **Test download button**: consistent “DEMO” naming.

---

## 5. Localization Report

| Component | Status |
|-----------|--------|
| Bot messages (`bot/ui/messages.py`) | ✅ Uzbek (Latin) |
| WebApp | ✅ `webapp/locales/uz.json` + inline fallback |
| Default language | ✅ `uz` only (`SUPPORTED_LANGS = ['uz']`) |
| Document template | ✅ Uzbek labels via `L` object |
| Payment texts | ✅ Uzbek |
| Error messages (API) | ✅ Uzbek |

---

## 6. Security Improvements

1. **Export endpoints require auth**: `/api/export_cv`, `/api/export_obyektivka`, `/api/generate_obyektivka` return 401 without valid session.
2. **Preview always watermarked**: server overrides client `watermark`/`mask_pii` flags.
3. **Payload sanitization**: strips watermark flags from paid request payloads before storage.
4. **Existing controls preserved**: `paid_doc_download` checks user ownership + approval status; export guard + quota consumption.

---

## 7. Files Changed (Summary)

| File | Change |
|------|--------|
| `bot/services/render_service.py` | Playwright browser pool |
| `bot/services/document_render/watermark.py` | Demo banner + configurable text |
| `bot/services/document_render/context.py` | Preview banner in render context |
| `bot/services/document_render/photo.py` | `compress_payload_photo()` |
| `templates/obyektivka_template.html` | Demo banner overlay |
| `backend/routers/documents_web.py` | Auth hardening, payload sanitize, preview force-WM |
| `backend/services/oby_preview_cache.py` | TTL + template revision |
| `webapp/locales/uz.json` | **New** — full Uzbek strings |
| `webapp/app.js` | Inline locale fallback, uz-only |
| `webapp/theme.css` | Loading/validation/toast styles |
| `webapp/obyektivka.html` | Preview note text |
| `webapp/js/obyektivka-preview.js` | DEMO filename |
| `bot/ui/messages.py` | Demo preview in instructions |
| `bot/ui/keyboards.py` | My documents in inline menu |
| `.env.example` | Watermark + performance vars |

---

## 8. Recommended Next Steps (Not in scope)

- Automated payment gateway (Click/Payme)
- Redis-backed preview cache for multi-worker deploys
- Remove legacy `aiogram` stubs and unused docker Celery worker
- Expand test coverage for payment + export flows

---

## 9. Environment Variables (New/Updated)

```env
DOC_WATERMARK_TEXT=DEMO VERSIYA · @DastyorAiBot
DOC_PREVIEW_BANNER_TEXT=DEMO VERSIYA — FAQAT KO'RISH UCHUN
DOC_WATERMARK_OPACITY=0.10
PLAYWRIGHT_BROWSER_MAX_USES=40
OBY_PREVIEW_CACHE_TTL_SECONDS=60
```
