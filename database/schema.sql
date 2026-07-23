-- Hujjatchi AI — SQLite production schema (database/app.db)

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ── users ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id         INTEGER NOT NULL UNIQUE,
    username            TEXT,
    full_name           TEXT,
    first_name          TEXT,
    last_name           TEXT,
    first_seen_at       TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen_at        TEXT,
    last_active_at      TEXT,
    total_cv            INTEGER NOT NULL DEFAULT 0,
    total_obyektivka    INTEGER NOT NULL DEFAULT 0,
    total_purchases     INTEGER NOT NULL DEFAULT 0,
    credits             INTEGER NOT NULL DEFAULT 0 CHECK (credits >= 0),
    is_blocked          INTEGER NOT NULL DEFAULT 0,
    referred_by_id      INTEGER,
    referred_active     INTEGER NOT NULL DEFAULT 0,
    referred_paid       INTEGER NOT NULL DEFAULT 0,
    referred_active_at  TEXT,
    referrals_rewarded_batches INTEGER NOT NULL DEFAULT 0,
    pay_promo_expires_at TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_users_telegram ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_last_seen ON users(last_seen_at);
CREATE INDEX IF NOT EXISTS idx_users_created ON users(created_at DESC);

-- ── payments ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS payments (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_number          TEXT UNIQUE,
    user_id                 INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    payer_name              TEXT NOT NULL DEFAULT '',
    card_number             TEXT NOT NULL DEFAULT '',
    document_type           TEXT,
    amount                  INTEGER NOT NULL DEFAULT 0,
    package_id              TEXT,
    credits_granted         INTEGER NOT NULL DEFAULT 1,
    promo_bonus_granted     INTEGER NOT NULL DEFAULT 0,
    status                  TEXT NOT NULL DEFAULT 'PENDING'
                            CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
    screenshot_path         TEXT,
    receipt_path            TEXT,
    admin_note              TEXT,
    approved_by             INTEGER,
    approved_at             TEXT,
    pending_reminder_sent_at TEXT,
    created_at              TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at              TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_user_status ON payments(user_id, status);
CREATE INDEX IF NOT EXISTS idx_payments_number ON payments(payment_number);
CREATE INDEX IF NOT EXISTS idx_payments_created ON payments(created_at DESC);

-- ── documents (access / export registry) ───────────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_type   TEXT NOT NULL CHECK (document_type IN ('cv', 'obyektivka')),
    file_path       TEXT,
    is_unlocked     INTEGER NOT NULL DEFAULT 0,
    payment_id      INTEGER REFERENCES payments(id) ON DELETE SET NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type);
CREATE INDEX IF NOT EXISTS idx_documents_created ON documents(created_at DESC);

-- ── cv_documents ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cv_documents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    template_name   TEXT,
    pdf_path        TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_cv_documents_user ON cv_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_cv_documents_created ON cv_documents(created_at DESC);

-- ── obyektivka_documents ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS obyektivka_documents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    docx_path       TEXT NOT NULL,
    pdf_preview_path TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_oby_documents_user ON obyektivka_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_oby_documents_created ON obyektivka_documents(created_at DESC);

-- ── support_messages ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS support_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message         TEXT NOT NULL,
    admin_reply     TEXT,
    status          TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'replied', 'closed')),
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_support_user ON support_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_support_status ON support_messages(status);
CREATE INDEX IF NOT EXISTS idx_support_created ON support_messages(created_at DESC);

-- ── admin_logs ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS admin_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id        INTEGER NOT NULL,
    action          TEXT NOT NULL,
    details         TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_admin_logs_admin ON admin_logs(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_logs_created ON admin_logs(created_at DESC);

-- ── settings ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS settings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    key             TEXT NOT NULL UNIQUE,
    value           TEXT NOT NULL,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO settings (key, value) VALUES ('maintenance_mode', '0');
INSERT OR IGNORE INTO settings (key, value) VALUES ('payment_card_number', '');
INSERT OR IGNORE INTO settings (key, value) VALUES ('payment_card_owner', '');

-- ── legacy app tables (voice AI, form drafts, admin feed) ────────────────────
CREATE TABLE IF NOT EXISTS cv_data (
    user_id         INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    full_name       TEXT,
    phone           TEXT,
    email           TEXT,
    address         TEXT,
    birth_date      TEXT,
    education       TEXT,
    experience      TEXT,
    skills          TEXT,
    languages       TEXT,
    extra           TEXT,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS obyektivka_data (
    user_id         INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    payload         TEXT NOT NULL DEFAULT '{}',
    pending_payload TEXT,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ai_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_type    TEXT NOT NULL CHECK (session_type IN ('cv_voice', 'oby_voice')),
    transcript      TEXT,
    extracted_data  TEXT,
    status          TEXT NOT NULL DEFAULT 'active',
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_ai_sessions_user ON ai_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_sessions_user_type
    ON ai_sessions(user_id, session_type, created_at DESC);

CREATE TABLE IF NOT EXISTS activity_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type      TEXT NOT NULL,
    user_id         INTEGER REFERENCES users(id) ON DELETE SET NULL,
    actor_name      TEXT,
    detail          TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_activity_created ON activity_events(created_at DESC);

CREATE TABLE IF NOT EXISTS error_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    category        TEXT NOT NULL,
    message         TEXT NOT NULL,
    details         TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_error_logs_category ON error_logs(category, created_at DESC);

-- Unified read view for admin statistics (cv + obyektivka exports)
CREATE VIEW IF NOT EXISTS generated_files AS
SELECT
    id,
    user_id,
    'cv' AS file_type,
    pdf_path AS file_path,
    template_name AS file_name,
    created_at
FROM cv_documents
UNION ALL
SELECT
    id,
    user_id,
    'obyektivka' AS file_type,
    docx_path AS file_path,
    NULL AS file_name,
    created_at
FROM obyektivka_documents;
