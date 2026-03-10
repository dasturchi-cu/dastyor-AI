# Obyektivka — FastAPI Arxitektura va 1:1 Dizayn

## Zanjir

```
webapp/obyektivka.html  →  exportWord()  →  POST /api/generate_obyektivka
                                                       ↓
                                          api_webhook.py  →  generate_obyektivka_docx()
                                                       ↓
                                          doc_generator.py  →  .docx  →  FileResponse + Telegram
```

## 1:1 Preview — Word Dizayn Xaritasi

| HTML (obyektivka.html) | doc_generator.py | Qiyos |
|------------------------|------------------|-------|
| `.doc-title` 18pt, bold, center, letter-spacing 5px | `_run(..., size=18.0, bold)` | ✓ |
| `.doc-photo` 30mm×40mm, border dashed #bbb | `Cm(3)×Cm(4)`, `_bdr_dashed` | ✓ |
| `.doc-name-label` 8pt, #777 | `_run(..., size=8.0, GREY_TXT)` | ✓ |
| `.doc-name` 16pt, bold | `_run(..., size=16.0, bold)` | ✓ |
| `.doc-info-lbl` 7.5pt, #666 | `_run(..., size=7.5, GREY_TXT)` | ✓ |
| `.doc-info-val` 11pt, #111 | `_run(..., size=11.0, DARK)` | ✓ |
| `.doc-section-title` 12pt, bold, border-bottom 2px | `_sect_title` 12.5pt, `_para_bdr_bot` | ✓ |
| `.doc-exp-table` thead #f2f2f2, 1px #999 | `_work_table`: shading F0F0F0, `_bdr_all(BLK)` | ✓ |
| `.doc-rel-table` 13/19/18/28/22% | `_col_w(t,pw,[13,19,18,28,22])` | ✓ |

## API Schema

### POST /api/generate_obyektivka

**Request (JSON):**
```json
{
  "telegram_id": 123456,
  "token": "...",
  "format": "word",
  "lang": "uz_lat",
  "fullname": "Familiya Ism Sharif",
  "birthdate": "1990 yil 15 yanvar",
  "birthplace": "Toshkent",
  "nation": "",
  "party": "",
  "education": "",
  "graduated": "",
  "specialty": "",
  "degree": "",
  "scientific_title": "",
  "languages": "",
  "military_rank": "",
  "awards": "",
  "deputy": "",
  "address": "",
  "phone": "",
  "work_experience": [{"year": "2005-2010", "position": "Ish joyi"}],
  "relatives": [{"degree": "Ota", "fullname": "...", "birth_year_place": "", "work_place": "", "address": ""}]
}
```

**Response:** `application/vnd.openxmlformats-officedocument.wordprocessingml.document` (stream)

### Pydantic Model (api_webhook.py)

```python
class ObyektivkaRequest(BaseModel):
    telegram_id: Optional[int] = None
    token: Optional[str] = None
    format: str = "word"
    lang: str = "uz_lat"
    fullname: str = ""
    birthdate: str = ""
    birthplace: str = ""
    # ... qolganlar
    work_experience: list = []
    relatives: list = []
```

## SQL Schema (Obyektivka eksport loglari uchun)

```sql
CREATE TABLE IF NOT EXISTS obyektivka_exports (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     BIGINT REFERENCES users(id),
    fullname    TEXT,
    format      VARCHAR(10) DEFAULT 'word',
    lang        VARCHAR(10) DEFAULT 'uz_lat',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_obyektivka_user ON obyektivka_exports(user_id);
```

## Ishga tushirish

```bash
uvicorn api_webhook:app --host 0.0.0.0 --port 8000
```
