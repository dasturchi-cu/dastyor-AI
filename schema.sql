-- DASTYOR AI — Barcha SQL (PostgreSQL / Supabase)
-- SQL editorga to'g'ridan-to'g'ri copy-paste qilish uchun

-- 1. users
CREATE TABLE IF NOT EXISTS users (
    id                BIGINT PRIMARY KEY,
    first_name        TEXT NOT NULL,
    username          TEXT,
    joined_at         TIMESTAMPTZ DEFAULT NOW(),
    last_active       TIMESTAMPTZ DEFAULT NOW(),
    interaction_count INTEGER DEFAULT 0,
    activity_count    INTEGER DEFAULT 0,
    files_processed   INTEGER DEFAULT 0,
    sessions          INTEGER DEFAULT 0,
    chat_id           BIGINT NOT NULL,
    lang              VARCHAR(10) DEFAULT 'uz_lat',
    feedback_count    INTEGER DEFAULT 0,
    blocked_bot       BOOLEAN DEFAULT FALSE,
    is_banned         BOOLEAN DEFAULT FALSE,
    ban_reason        TEXT,
    ban_date          TIMESTAMPTZ,
    last_service      VARCHAR(50)
);

-- 2. premium_subscriptions
CREATE TABLE IF NOT EXISTS premium_subscriptions (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    BIGINT REFERENCES users(id),
    granted_by TEXT,
    start_date TIMESTAMPTZ DEFAULT NOW(),
    end_date   TIMESTAMPTZ NOT NULL
);

-- 3. daily_usage
CREATE TABLE IF NOT EXISTS daily_usage (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    BIGINT REFERENCES users(id),
    usage_date DATE NOT NULL DEFAULT CURRENT_DATE,
    count      INTEGER DEFAULT 0,
    UNIQUE (user_id, usage_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_usage_user ON daily_usage(user_id);

-- 4. bot_settings
CREATE TABLE IF NOT EXISTS bot_settings (
    id               INTEGER PRIMARY KEY CHECK (id = 1),
    daily_limit      INTEGER DEFAULT 10,
    maintenance_mode BOOLEAN DEFAULT FALSE
);

INSERT INTO bot_settings (id, daily_limit, maintenance_mode)
VALUES (1, 10, FALSE)
ON CONFLICT (id) DO NOTHING;

-- 5. mandatory_channels
CREATE TABLE IF NOT EXISTS mandatory_channels (
    channel_id BIGINT PRIMARY KEY,
    name       TEXT NOT NULL,
    url        TEXT NOT NULL
);

-- 6. obyektivka_exports
CREATE TABLE IF NOT EXISTS obyektivka_exports (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    BIGINT REFERENCES users(id),
    fullname   TEXT,
    format     VARCHAR(10) DEFAULT 'word',
    lang       VARCHAR(10) DEFAULT 'uz_lat',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_obyektivka_user ON obyektivka_exports(user_id);
