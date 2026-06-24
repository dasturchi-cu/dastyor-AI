# Cache revision — qachon yangilash kerak?

Bu loyihada **2 xil cache** bor. Ularni **har deployda emas**, faqat tegishli fayl o‘zgarganda yangilang.

---

## 1. `WEBAPP_VERSION` — Telegram WebApp (brauzer cache)

**Nima qiladi:** Bot WebApp linkiga `?v=...` qo‘shadi. Foydalanuvchi eski `obyektivka.html` / `app.js` ni ko‘rmasin.

**Qachon oshirish kerak** (bittasi yetarli):

- `webapp/obyektivka.html`
- `webapp/cv.html`
- `webapp/app.js`
- `webapp/js/*.js`
- `webapp/css/*`

**Qachon kerak emas:** backend, to‘lov, admin, DB, bot handler.

**Qayerda yangilash:**

| Fayl | O‘zgaruvchi |
|------|-------------|
| `.env` | `WEBAPP_VERSION=20260625a` |
| `.env.example` | xuddi shu |
| Railway Variables | `WEBAPP_VERSION` |

**Format:** sana + harf, masalan `20260625a`, `20260625b` (ketma-ket oshiring).

---

## 2. `OBY_PREVIEW_TEMPLATE_REVISION` — server preview cache (Obyektivka)

**Nima qiladi:** Server 60 soniya HTML/PDF preview cache saqlaydi. Revision o‘zgarsa eski preview ishlatilmaydi.

**Qachon oshirish kerak:**

- `templates/obyektivka_template.html`
- `features/obyektivka/malumotnoma_data.py`
- `features/obyektivka/placeholders.py`
- `features/obyektivka/current_job.py`
- `backend/services/document_render/context.py`
- `templates/obyektivka_master.docx` yoki DOCX layout/polish

**Qachon kerak emas:** to‘lov, admin, oddiy API, `webapp/*` (buning uchun `WEBAPP_VERSION`).

**Qayerda yangilash:**

| Fayl | O‘zgaruvchi |
|------|-------------|
| `.env` | `OBY_PREVIEW_TEMPLATE_REVISION=20260625-oby-fix` |
| `.env.example` | xuddi shu |
| `backend/services/oby_preview_cache.py` | default qiymat (13-qator) |
| Railway Variables | `OBY_PREVIEW_TEMPLATE_REVISION` |

**Format:** `YYYYMMDD-qisqa-tavsif`, masalan `20260624-employment-ssot`.

---

## 3. `CV_PREVIEW_TEMPLATE_REVISION` — server preview cache (CV)

**Qachon oshirish kerak:**

- `templates/cv_template.html`
- CV render / PDF mapper o‘zgarsa

**Qayerda:** `.env`, `.env.example`, `backend/services/cv_preview_cache.py`, Railway.

---

## Tez jadval

| O‘zgartirdingiz | Yangilang |
|-----------------|-----------|
| `webapp/obyektivka.html` | `WEBAPP_VERSION` |
| `webapp/js/obyektivka-preview.js` | `WEBAPP_VERSION` + `obyektivka.html` ichidagi `?v=` (script) |
| `templates/obyektivka_template.html` | `OBY_PREVIEW_TEMPLATE_REVISION` |
| `malumotnoma_data.py` / preview mapper | `OBY_PREVIEW_TEMPLATE_REVISION` |
| To‘lov / admin / bot | **hech narsa** |
| Ikkalasi ham o‘zgarsa | **ikkalasini ham** |

---

## Railway deploy

Lokal `.env` Railway ga avtomatik ketmaydi. Production uchun **Railway → Variables** da ham qo‘ying:

```
WEBAPP_VERSION=...
OBY_PREVIEW_TEMPLATE_REVISION=...
CV_PREVIEW_TEMPLATE_REVISION=...   # faqat CV shablon o‘zgarsa
```

Keyin **Redeploy**.

---

## Cursor agent qoidasi

`.cursor/rules/cache-revisions.mdc` — agent tegishli faylni o‘zgartirganda revisionlarni **o‘zi yangilaydi**, sizdan so‘ramaydi.

Siz faqat deploy qiling; qaysi revision kerakligini eslab qolish shart emas.
